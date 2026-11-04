package services

import (
	"encoding/json"
	"io"
	"testing"
	"time"

	"github.com/sirupsen/logrus"
	apimodels "grcinsight/internal/models"
)

type configCapturingPython struct {
	calls   int
	payload []byte
}

func (f *configCapturingPython) IsAsync() bool { return true }
func (f *configCapturingPython) RunWorkflow(_ *apimodels.WorkflowRequest) (*apimodels.WorkflowResponse, error) {
	panic("synchronous workflow unexpected")
}
func (f *configCapturingPython) RunWorkflowAsync(req *apimodels.WorkflowRequest, reportID string) error {
	f.calls++
	var err error
	f.payload, err = marshalWorkflowPayload(req, reportID, time.Time{})
	return err
}

func TestGenerateReportOmittedOutputReachesPythonAsDefault(t *testing.T) {
	for _, input := range []string{
		`{"feed_url":"https://feed.example.test/rss","config":{"model":"openrouter/vendor/model:free"}}`,
		`{"feed_url":"https://feed.example.test/rss"}`,
	} {
		var req apimodels.GenerateReportRequest
		if err := json.Unmarshal([]byte(input), &req); err != nil {
			t.Fatal(err)
		}
		repo, python := &fakeReportRepo{}, &configCapturingPython{}
		logger := logrus.New()
		logger.SetOutput(io.Discard)
		service := NewReportService(repo, &fakeArticleRepo2{}, python, logger)
		if _, err := service.GenerateReport(&req); err != nil {
			t.Fatal(err)
		}
		var event struct {
			Config struct {
				MaxTokens int `json:"max_tokens"`
			} `json:"config"`
		}
		if err := json.Unmarshal(python.payload, &event); err != nil {
			t.Fatal(err)
		}
		if python.calls != 1 || repo.created == nil || event.Config.MaxTokens != 16000 {
			t.Fatalf("wrong default handoff: calls=%d cap=%d", python.calls, event.Config.MaxTokens)
		}
		t.Logf("workflow_contract_payload=%s", python.payload)
	}
}

func TestGenerateReportInvalidOutputCannotCreateProcessingRecord(t *testing.T) {
	for _, cap := range []int{-1, 16001} {
		repo, python := &fakeReportRepo{}, &configCapturingPython{}
		logger := logrus.New()
		logger.SetOutput(io.Discard)
		service := NewReportService(repo, &fakeArticleRepo2{}, python, logger)
		_, err := service.GenerateReport(&apimodels.GenerateReportRequest{
			FeedURL: "https://feed.example.test/rss", Config: apimodels.GRCAnalysisConfig{MaxTokens: cap},
		})
		if err == nil || repo.created != nil || python.calls != 0 {
			t.Fatal("invalid allowance created state or entered Python workflow")
		}
	}
}
