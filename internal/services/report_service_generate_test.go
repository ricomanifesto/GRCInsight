package services

import (
	"encoding/json"
	"fmt"
	"io"
	"reflect"
	"strings"
	"testing"
	"time"

	"errors"

	"grcinsight/internal/database/dynamodb"
	dbmodels "grcinsight/internal/database/models"
	apimodels "grcinsight/internal/models"

	"github.com/sirupsen/logrus"
)

// fakeReportRepo implements ReportRepository for testing GenerateReport
type fakeReportRepo struct {
	created     *dbmodels.Report
	updated     *dbmodels.Report
	stored      *dbmodels.Report
	failed      []string
	finalOnFail bool
}

func (f *fakeReportRepo) Create(r *dbmodels.Report) error {
	r.ID = "rep_test"
	now := time.Now()
	r.CreatedAt = now
	r.UpdatedAt = now
	f.created = r
	return nil
}
func (f *fakeReportRepo) GetByID(id string) (*dbmodels.Report, error) { return f.stored, nil }
func (f *fakeReportRepo) List(limit, offset int) ([]*dbmodels.Report, int64, error) {
	return nil, 0, nil
}
func (f *fakeReportRepo) Update(r *dbmodels.Report) error                       { f.updated = r; return nil }
func (f *fakeReportRepo) Delete(id string) error                                { return nil }
func (f *fakeReportRepo) GetByStatus(status string) ([]*dbmodels.Report, error) { return nil, nil }
func (f *fakeReportRepo) MarkFailedIfOpen(id, reason string) error {
	if f.finalOnFail {
		return dynamodb.ErrReportFinal
	}
	f.failed = append(f.failed, reason)
	return nil
}

// fakePythonClient stands in for the Python report writer.
type fakePythonClient struct {
	async  bool
	err    error
	jobs   []WorkflowJob
	commit func(job WorkflowJob)
}

func (f *fakePythonClient) IsAsync() bool { return f.async }
func (f *fakePythonClient) RunWorkflowAsync(req *apimodels.WorkflowRequest, job WorkflowJob) error {
	f.jobs = append(f.jobs, job)
	return f.err
}
func (f *fakePythonClient) RunWorkflowForReport(req *apimodels.WorkflowRequest, job WorkflowJob) error {
	f.jobs = append(f.jobs, job)
	if f.err == nil && f.commit != nil {
		f.commit(job)
	}
	return f.err
}
func (f *fakePythonClient) HealthCheck() error { return nil }

// fakeArticleRepo tracks CreateForReport calls
type fakeArticleRepo2 struct{ calls int }

func (f *fakeArticleRepo2) Create(a *dbmodels.Article) error { f.calls++; return nil }
func (f *fakeArticleRepo2) CreateForReport(reportID string, a *dbmodels.Article) error {
	f.calls++
	return nil
}
func (f *fakeArticleRepo2) GetByID(id uint) (*dbmodels.Article, error)     { return nil, nil }
func (f *fakeArticleRepo2) GetByURL(url string) (*dbmodels.Article, error) { return nil, nil }
func (f *fakeArticleRepo2) List(limit, offset int) ([]*dbmodels.Article, int64, error) {
	return nil, 0, nil
}
func (f *fakeArticleRepo2) Update(a *dbmodels.Article) error { return nil }
func (f *fakeArticleRepo2) Delete(id uint) error             { return nil }
func (f *fakeArticleRepo2) GetGRCArticles(limit, offset int) ([]*dbmodels.Article, int64, error) {
	return nil, 0, nil
}
func (f *fakeArticleRepo2) GetByReportID(reportID string, limit, offset int) ([]*dbmodels.Article, int64, error) {
	return nil, 0, nil
}

func newGenerateService(fr *fakeReportRepo, fa *fakeArticleRepo2, pc *fakePythonClient) *ReportService {
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	return &ReportService{reportRepo: fr, articleRepo: fa, pythonClient: pc, logger: logger}
}

var generateRequest = &apimodels.GenerateReportRequest{
	FeedURL: "https://example.com/rss",
	Config:  apimodels.GRCAnalysisConfig{Model: "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", MaxTokens: 16000},
}

// Synchronous generation lets the Python report writer complete the admitted job
// and returns the stored row; Go writes neither the outcome nor article rows.
func TestGenerateReport_SyncDelegatesCompletionToTheReportWriter(t *testing.T) {
	const metadataJSON = `{
		"article_count": 1, "grc_article_count": 1,
		"analysis_mode": "model", "fallback_reason": null,
		"source_articles": [{"title": "A1", "url": "https://ex.com/1", "cves": ["CVE-2026-12345"]}],
		"report_plan": {"executive_brief": {"decision_frame": "governance", "source_ids": [1]}},
		"regulations_mentioned": [], "frameworks_referenced": []
	}`
	var written map[string]any
	if err := json.Unmarshal([]byte(metadataJSON), &written); err != nil {
		t.Fatal(err)
	}
	fr := &fakeReportRepo{}
	fa := &fakeArticleRepo2{}
	pc := &fakePythonClient{}
	pc.commit = func(job WorkflowJob) {
		fr.stored = &dbmodels.Report{
			ID: job.ReportID, Status: dbmodels.StatusCompleted, Content: "Hello",
			JobID: job.JobID, TerminalOutcome: "model_completed", Metadata: written,
		}
	}
	report, err := newGenerateService(fr, fa, pc).GenerateReport(generateRequest)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(pc.jobs) != 1 || pc.jobs[0].ReportID != "rep_test" || pc.jobs[0].JobID != fr.created.JobID {
		t.Fatalf("writer not given the admitted job: %+v", pc.jobs)
	}
	if !strings.HasPrefix(fr.created.JobID, "job_") {
		t.Fatalf("report created without a job id: %q", fr.created.JobID)
	}
	if fr.updated != nil || fa.calls != 0 {
		t.Fatal("Go wrote the outcome or article rows itself")
	}
	if report.Status != dbmodels.StatusCompleted || report.TerminalOutcome != "model_completed" {
		t.Fatalf("stored outcome not returned: %+v", report)
	}
	// Metadata is returned exactly as the writer stored it.
	encoded, _ := json.Marshal(report.Metadata)
	var stored map[string]any
	_ = json.Unmarshal(encoded, &stored)
	if !reflect.DeepEqual(stored, written) {
		t.Fatalf("stored metadata changed:\n got: %#v\nwant: %#v", stored, written)
	}
}

func TestGenerateReport_SyncFailureIsRecordedOnlyWhileOpen(t *testing.T) {
	fr := &fakeReportRepo{}
	pc := &fakePythonClient{err: errors.New("python service returned 502")}
	if _, err := newGenerateService(fr, &fakeArticleRepo2{}, pc).GenerateReport(generateRequest); err == nil {
		t.Fatal("expected an error")
	}
	if len(fr.failed) != 1 || fr.failed[0] != "workflow_failed" {
		t.Fatalf("failure not recorded: %v", fr.failed)
	}
	// A final outcome (for example committed before a transport timeout) is left alone.
	final := &fakeReportRepo{finalOnFail: true}
	if _, err := newGenerateService(final, &fakeArticleRepo2{}, pc).GenerateReport(generateRequest); err == nil {
		t.Fatal("expected an error")
	}
	if len(final.failed) != 0 || final.updated != nil {
		t.Fatal("final report changed")
	}
}

func TestGenerateReport_RefusedCompletionIsNotMarkedFailed(t *testing.T) {
	fr := &fakeReportRepo{}
	pc := &fakePythonClient{err: fmt.Errorf("%w: foreign_completion_refused", ErrCompletionRefused)}
	if _, err := newGenerateService(fr, &fakeArticleRepo2{}, pc).GenerateReport(generateRequest); err == nil {
		t.Fatal("expected an error")
	}
	if len(fr.failed) != 0 {
		t.Fatalf("refusal recorded as failure: %v", fr.failed)
	}
}

func TestGenerateReport_AsyncPassesTheJobAndRecordsInvokeFailure(t *testing.T) {
	fr := &fakeReportRepo{}
	pc := &fakePythonClient{async: true}
	report, err := newGenerateService(fr, &fakeArticleRepo2{}, pc).GenerateReport(generateRequest)
	if err != nil || report.Status != dbmodels.StatusProcessing {
		t.Fatalf("unexpected result: %+v %v", report, err)
	}
	if pc.jobs[0].JobID == "" || pc.jobs[0].JobID != fr.created.JobID {
		t.Fatalf("async invocation without the admitted job: %+v", pc.jobs)
	}
	failing := &fakeReportRepo{}
	pc = &fakePythonClient{async: true, err: errors.New("throttled")}
	if _, err := newGenerateService(failing, &fakeArticleRepo2{}, pc).GenerateReport(generateRequest); err == nil {
		t.Fatal("expected an error")
	}
	if len(failing.failed) != 1 || failing.failed[0] != "invocation_failed" {
		t.Fatalf("invoke failure not recorded: %v", failing.failed)
	}
}
