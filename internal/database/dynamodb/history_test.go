package dynamodb

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"sort"
	"strings"
	"testing"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/sirupsen/logrus"
)

// fakeAPI keeps items per table and applies DynamoDB's paging, batch and
// conditional-write behaviour for the request shapes this package issues.
type fakeAPI struct {
	tables         map[string]map[string]map[string]types.AttributeValue
	queryPages     int
	gets           int
	lastConsistent bool
}

func newFakeAPI() *fakeAPI {
	return &fakeAPI{tables: map[string]map[string]map[string]types.AttributeValue{
		TableName:     {},
		ArticlesTable: {},
	}}
}

func keyName(table string) string {
	if table == TableName {
		return "report_id"
	}
	return "article_id"
}

func str(av types.AttributeValue) string {
	if s, ok := av.(*types.AttributeValueMemberS); ok {
		return s.Value
	}
	return ""
}

func (f *fakeAPI) put(table string, item map[string]types.AttributeValue) {
	f.tables[table][str(item[keyName(table)])] = item
}

func (f *fakeAPI) GetItem(_ context.Context, in *dynamodb.GetItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.GetItemOutput, error) {
	f.gets++
	f.lastConsistent = aws.ToBool(in.ConsistentRead)
	table := aws.ToString(in.TableName)
	return &dynamodb.GetItemOutput{Item: f.tables[table][str(in.Key[keyName(table)])]}, nil
}

func (f *fakeAPI) PutItem(_ context.Context, in *dynamodb.PutItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.PutItemOutput, error) {
	table := aws.ToString(in.TableName)
	key := str(in.Item[keyName(table)])
	if strings.Contains(aws.ToString(in.ConditionExpression), "attribute_not_exists") {
		if _, exists := f.tables[table][key]; exists {
			return nil, &types.ConditionalCheckFailedException{}
		}
	}
	f.tables[table][key] = in.Item
	return &dynamodb.PutItemOutput{}, nil
}

func (f *fakeAPI) UpdateItem(_ context.Context, in *dynamodb.UpdateItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.UpdateItemOutput, error) {
	table := aws.ToString(in.TableName)
	key := str(in.Key[keyName(table)])
	item, exists := f.tables[table][key]
	cond := aws.ToString(in.ConditionExpression)
	if strings.Contains(cond, "attribute_exists(report_id)") && !exists {
		return nil, &types.ConditionalCheckFailedException{}
	}
	if strings.Contains(cond, "#status IN (:pending, :processing)") {
		status := str(item["status"])
		_, final := item[OutcomeGuard]
		if (status != StatusPending && status != StatusProcessing) || final {
			return nil, &types.ConditionalCheckFailedException{}
		}
	}
	// Apply "SET a = :v, #n = :w" assignments.
	updated := map[string]types.AttributeValue{}
	for k, v := range item {
		updated[k] = v
	}
	for _, part := range strings.Split(strings.TrimPrefix(aws.ToString(in.UpdateExpression), "SET "), ",") {
		pieces := strings.SplitN(strings.TrimSpace(part), " = ", 2)
		name := pieces[0]
		if resolved, ok := in.ExpressionAttributeNames[name]; ok {
			name = resolved
		}
		updated[name] = in.ExpressionAttributeValues[strings.TrimSpace(pieces[1])]
	}
	f.tables[table][key] = updated
	return &dynamodb.UpdateItemOutput{}, nil
}

func (f *fakeAPI) DeleteItem(context.Context, *dynamodb.DeleteItemInput, ...func(*dynamodb.Options)) (*dynamodb.DeleteItemOutput, error) {
	return &dynamodb.DeleteItemOutput{}, nil
}

// Query serves the by-report-id index in key order with Limit/LastEvaluatedKey paging.
func (f *fakeAPI) Query(_ context.Context, in *dynamodb.QueryInput, _ ...func(*dynamodb.Options)) (*dynamodb.QueryOutput, error) {
	f.queryPages++
	rid := str(in.ExpressionAttributeValues[":rid"])
	var keys []string
	for k, item := range f.tables[ArticlesTable] {
		if str(item["report_id"]) == rid {
			keys = append(keys, k)
		}
	}
	sort.Strings(keys)
	if in.ExclusiveStartKey != nil {
		after := str(in.ExclusiveStartKey["article_id"])
		i := sort.SearchStrings(keys, after)
		if i < len(keys) && keys[i] == after {
			i++
		}
		keys = keys[i:]
	}
	limit := int(aws.ToInt32(in.Limit))
	out := &dynamodb.QueryOutput{}
	if limit > 0 && len(keys) > limit {
		keys = keys[:limit]
		out.LastEvaluatedKey = map[string]types.AttributeValue{
			"article_id": &types.AttributeValueMemberS{Value: keys[len(keys)-1]},
		}
	}
	for _, k := range keys {
		out.Items = append(out.Items, f.tables[ArticlesTable][k])
	}
	return out, nil
}

func (f *fakeAPI) Scan(context.Context, *dynamodb.ScanInput, ...func(*dynamodb.Options)) (*dynamodb.ScanOutput, error) {
	return &dynamodb.ScanOutput{}, nil
}

func (f *fakeAPI) DescribeTable(context.Context, *dynamodb.DescribeTableInput, ...func(*dynamodb.Options)) (*dynamodb.DescribeTableOutput, error) {
	return &dynamodb.DescribeTableOutput{}, nil
}

// decodeTyped converts DynamoDB typed JSON into attribute values.
func decodeTyped(t *testing.T, raw map[string]any) types.AttributeValue {
	t.Helper()
	for kind, v := range raw {
		switch kind {
		case "S":
			return &types.AttributeValueMemberS{Value: v.(string)}
		case "N":
			return &types.AttributeValueMemberN{Value: v.(string)}
		case "BOOL":
			return &types.AttributeValueMemberBOOL{Value: v.(bool)}
		case "NULL":
			return &types.AttributeValueMemberNULL{Value: true}
		case "L":
			var list []types.AttributeValue
			for _, e := range v.([]any) {
				list = append(list, decodeTyped(t, e.(map[string]any)))
			}
			return &types.AttributeValueMemberL{Value: list}
		case "M":
			m := map[string]types.AttributeValue{}
			for k, e := range v.(map[string]any) {
				m[k] = decodeTyped(t, e.(map[string]any))
			}
			return &types.AttributeValueMemberM{Value: m}
		}
	}
	t.Fatalf("unsupported attribute %v", raw)
	return nil
}

// loadWriterFixture loads the items the Python report writer stored in its scenarios.
func loadWriterFixture(t *testing.T) (*fakeAPI, *Repository) {
	t.Helper()
	data, err := os.ReadFile("testdata/history-items.json")
	if err != nil {
		t.Fatal(err)
	}
	var tables map[string][]map[string]map[string]any
	if err := json.Unmarshal(data, &tables); err != nil {
		t.Fatal(err)
	}
	api := newFakeAPI()
	for table, items := range tables {
		for _, raw := range items {
			item := map[string]types.AttributeValue{}
			for k, v := range raw {
				item[k] = decodeTyped(t, v)
			}
			api.put(table, item)
		}
	}
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	return api, NewRepository(api, logger)
}

func TestRevisionDigestMatchesTheWriter(t *testing.T) {
	// Vector computed by the Python writer's canonical JSON digest.
	digest, ok := RevisionDigest(
		"https://news.example.test/a?b=1&c=<2>",
		"Quote \" back\\slash é 日本   end",
		"tab\tnl\ncr\rbs\bff\fctl\x01",
		"<p>x &amp; y</p>\x7f",
	)
	if !ok || digest != "806716debca899ee6544dca0480c9c05f8c3b60f239e642c0a7bb97e6fd8b68c" {
		t.Fatalf("digest mismatch: %s", digest)
	}
	capture := CaptureDigest(digest, 50010, strings.Repeat("ab", 32), "publisher_page", true)
	if capture != "68bba1a6a6340d7a4d422f452a8b5deb60f439b180a9adbe571f1f2c4e0e5d3f" {
		t.Fatalf("capture digest mismatch: %s", capture)
	}
	if _, ok := RevisionDigest("\xff", "", "", ""); ok {
		t.Fatal("invalid UTF-8 must not verify")
	}
}

func TestReportArticlesResolvesTheBoundRevisions(t *testing.T) {
	_, repo := loadWriterFixture(t)
	arts, total, err := repo.ReportArticles(context.Background(), "report_s2", 20, 0)
	if err != nil {
		t.Fatal(err)
	}
	if total != 2 || len(arts) != 2 {
		t.Fatalf("expected 2 bound articles, got total=%d len=%d", total, len(arts))
	}
	if !strings.HasSuffix(arts[0].URL, "/alpha") || !strings.HasSuffix(arts[1].URL, "/bravo") {
		t.Fatalf("appearances not in position order: %s, %s", arts[0].URL, arts[1].URL)
	}
	if arts[0].EvidenceStatus != EvidenceIntact || !strings.Contains(arts[0].Content, "revised") {
		t.Fatalf("changed revision not resolved: %q %q", arts[0].EvidenceStatus, arts[0].Content)
	}
	if arts[0].PublishedAtKnown == nil || !*arts[0].PublishedAtKnown || arts[0].PublishedAt == "" {
		t.Fatal("known publication time lost")
	}
}

func TestReportArticlesFlagsCorruptRevisionsWithoutTheirText(t *testing.T) {
	// The fixture's bravo revision was edited after it was written.
	_, repo := loadWriterFixture(t)
	arts, _, err := repo.ReportArticles(context.Background(), "report_s1", 20, 0)
	if err != nil {
		t.Fatal(err)
	}
	var bravo *Article
	for i := range arts {
		if strings.HasSuffix(arts[i].URL, "/bravo") {
			bravo = &arts[i]
		}
	}
	if bravo == nil || bravo.EvidenceStatus != EvidenceCorrupt || bravo.Content != "" {
		t.Fatalf("corrupt revision served as evidence: %+v", bravo)
	}
	if arts[0].EvidenceStatus != EvidenceIntact || arts[0].Content == "" {
		t.Fatalf("intact revision not served: %+v", arts[0])
	}
}

func TestReportArticlesReportsMissingRevisions(t *testing.T) {
	api, repo := loadWriterFixture(t)
	for k, item := range api.tables[ArticlesTable] {
		if str(item["record_kind"]) == RecordKindRevision && strings.Contains(str(item["url"]), "charlie") {
			delete(api.tables[ArticlesTable], k)
		}
	}
	arts, _, err := repo.ReportArticles(context.Background(), "report_s5", 20, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(arts) != 1 || arts[0].EvidenceStatus != EvidenceMissing || arts[0].Content != "" {
		t.Fatalf("missing revision not reported: %+v", arts)
	}
}

func TestReportArticlesKeepsLegacyRowsAsStored(t *testing.T) {
	_, repo := loadWriterFixture(t)
	arts, total, err := repo.ReportArticles(context.Background(), "report_20251001_090000_123", 20, 0)
	if err != nil {
		t.Fatal(err)
	}
	if total != 1 || arts[0].EvidenceStatus != EvidenceLegacy || arts[0].Content != "Legacy synthetic body." {
		t.Fatalf("legacy row changed: %+v", arts)
	}
}

func TestReportArticlesShowsUnboundAppearancesOnlyWithoutAFinalOutcome(t *testing.T) {
	api, repo := loadWriterFixture(t)
	// A stray appearance from a diverged retry must not join a bound report.
	stray := map[string]types.AttributeValue{}
	for k, v := range api.tables[ArticlesTable] {
		// The alpha appearance has an intact revision, so only binding is under test.
		if str(v["report_id"]) == "report_s2" && strings.HasSuffix(str(v["url"]), "/alpha") {
			for name, value := range v {
				stray[name] = value
			}
			stray["article_id"] = &types.AttributeValueMemberS{Value: k + "-stray"}
			break
		}
	}
	stray["appearance_set_sha256"] = &types.AttributeValueMemberS{Value: "diverged"}
	api.put(ArticlesTable, stray)
	_, total, err := repo.ReportArticles(context.Background(), "report_s2", 20, 0)
	if err != nil || total != 2 {
		t.Fatalf("unbound appearance listed for a final report: total=%d err=%v", total, err)
	}
	// A report without a final outcome binds nothing: rows are visible but labelled unbound.
	api.put(TableName, map[string]types.AttributeValue{
		"report_id": &types.AttributeValueMemberS{Value: "open_report"},
		"status":    &types.AttributeValueMemberS{Value: StatusProcessing},
	})
	orphan := map[string]types.AttributeValue{}
	for name, value := range stray {
		orphan[name] = value
	}
	orphan["article_id"] = &types.AttributeValueMemberS{Value: "aapp#open_report#x#0000"}
	orphan["report_id"] = &types.AttributeValueMemberS{Value: "open_report"}
	api.put(ArticlesTable, orphan)
	arts, _, err := repo.ReportArticles(context.Background(), "open_report", 20, 0)
	if err != nil || len(arts) != 1 || arts[0].EvidenceStatus != EvidenceUnbound {
		t.Fatalf("unbound appearance not labelled: %+v err=%v", arts, err)
	}
	// A missing revision outranks the unbound label.
	for k, item := range api.tables[ArticlesTable] {
		if str(item["record_kind"]) == RecordKindRevision && strings.HasSuffix(str(item["url"]), "/alpha") {
			delete(api.tables[ArticlesTable], k)
		}
	}
	arts, _, err = repo.ReportArticles(context.Background(), "open_report", 20, 0)
	if err != nil || arts[0].EvidenceStatus != EvidenceMissing {
		t.Fatalf("missing revision not reported for an unbound row: %+v err=%v", arts, err)
	}
}

func TestReportArticlesPagesWithinBounds(t *testing.T) {
	api, repo := loadWriterFixture(t)
	// Add 250 legacy rows to force multi-page queries.
	for i := 0; i < 250; i++ {
		id := fmt.Sprintf("a_legacy_%03d", i)
		api.put(ArticlesTable, map[string]types.AttributeValue{
			"article_id": &types.AttributeValueMemberS{Value: id},
			"report_id":  &types.AttributeValueMemberS{Value: "report_s2"},
			"url":        &types.AttributeValueMemberS{Value: "https://legacy.example.test/" + id},
		})
	}
	api.gets = 0
	arts, total, err := repo.ReportArticles(context.Background(), "report_s2", 100, 200)
	if err != nil {
		t.Fatal(err)
	}
	if total != 252 || len(arts) != 52 {
		t.Fatalf("expected total 252 and 52 rows, got %d and %d", total, len(arts))
	}
	if api.queryPages < 3 {
		t.Fatalf("expected paged queries, got %d", api.queryPages)
	}
	alpha, bravo := arts[50], arts[51]
	if alpha.RecordKind != RecordKindAppearance || alpha.EvidenceStatus != EvidenceIntact || alpha.Content == "" {
		t.Fatalf("revision text not resolved: %+v", alpha)
	}
	if bravo.EvidenceStatus != EvidenceCorrupt || bravo.Content != "" {
		t.Fatalf("tampered revision served: %+v", bravo)
	}
	// One report read plus one read per revision on the page, never per listed row.
	if api.gets != 3 {
		t.Fatalf("expected 3 bounded reads, got %d", api.gets)
	}
	empty, total, err := repo.ReportArticles(context.Background(), "report_s2", 10, 1000)
	if err != nil || len(empty) != 0 || total != 252 {
		t.Fatalf("offset past the end: len=%d total=%d err=%v", len(empty), total, err)
	}
}

func TestGuardedWritesNeverRewriteAFinalOutcome(t *testing.T) {
	api, repo := loadWriterFixture(t)
	ctx := context.Background()
	before := api.tables[TableName]["report_s1"]
	if err := repo.MarkReportFailedIfOpen(ctx, "report_s1", "late"); !errors.Is(err, ErrReportFinal) {
		t.Fatalf("expected ErrReportFinal, got %v", err)
	}
	if err := repo.UpdateReportStatus(ctx, "report_s1", StatusFailed); !errors.Is(err, ErrReportFinal) {
		t.Fatalf("expected ErrReportFinal from status update, got %v", err)
	}
	if err := repo.UpdateReport(ctx, &Report{ReportID: "report_s1", Status: StatusCompleted}); !errors.Is(err, ErrReportFinal) {
		t.Fatalf("expected ErrReportFinal from update, got %v", err)
	}
	// Legacy terminal rows have no digest but are final too.
	if err := repo.MarkReportFailedIfOpen(ctx, "report_20251001_090000_123", "late"); !errors.Is(err, ErrReportFinal) {
		t.Fatalf("legacy completed row reopened: %v", err)
	}
	if str(api.tables[TableName]["report_s1"]["status"]) != str(before["status"]) {
		t.Fatal("final report changed")
	}
}

func TestMarkReportFailedIfOpenRecordsAnExplainedFailure(t *testing.T) {
	api, repo := loadWriterFixture(t)
	api.put(TableName, map[string]types.AttributeValue{
		"report_id": &types.AttributeValueMemberS{Value: "open"},
		"status":    &types.AttributeValueMemberS{Value: StatusProcessing},
	})
	if err := repo.MarkReportFailedIfOpen(context.Background(), "open", "invocation_failed"); err != nil {
		t.Fatal(err)
	}
	row := api.tables[TableName]["open"]
	if str(row["status"]) != StatusFailed || str(row["terminal_reason"]) != "invocation_failed" {
		t.Fatalf("failure not recorded: %v", row)
	}
}

func TestCreateReportRefusesAnExistingID(t *testing.T) {
	api, repo := loadWriterFixture(t)
	before := api.tables[TableName]["report_s1"]
	err := repo.CreateReport(context.Background(), &Report{ReportID: "report_s1", Title: "x"})
	if err == nil {
		t.Fatal("existing report overwritten")
	}
	if str(api.tables[TableName]["report_s1"]["title"]) != str(before["title"]) {
		t.Fatal("existing report changed")
	}
}

func TestReportArticlesOfAnUnknownReportIsEmpty(t *testing.T) {
	_, repo := loadWriterFixture(t)
	arts, total, err := repo.ReportArticles(context.Background(), "no-such-report", 20, 0)
	if err != nil || total != 0 || len(arts) != 0 {
		t.Fatalf("unknown report: len=%d total=%d err=%v", len(arts), total, err)
	}
}

func TestGetReportConsistentUsesAStronglyConsistentRead(t *testing.T) {
	api, repo := loadWriterFixture(t)
	report, err := repo.GetReportConsistent(context.Background(), "report_s1")
	if err != nil || report.ReportID != "report_s1" || !api.lastConsistent {
		t.Fatalf("consistent read not requested: %+v consistent=%v err=%v", report, api.lastConsistent, err)
	}
	if _, err := repo.GetReport(context.Background(), "report_s1"); err != nil || api.lastConsistent {
		t.Fatalf("ordinary reads must stay eventually consistent: consistent=%v err=%v", api.lastConsistent, err)
	}
}

func TestReportArticlesRejectsTamperedCaptureProvenance(t *testing.T) {
	api, repo := loadWriterFixture(t)
	for _, item := range api.tables[ArticlesTable] {
		if str(item["record_kind"]) == RecordKindRevision && strings.Contains(str(item["url"]), "charlie") {
			item["content_truncated"] = &types.AttributeValueMemberBOOL{Value: true}
		}
	}
	arts, _, err := repo.ReportArticles(context.Background(), "report_s5", 20, 0)
	if err != nil || len(arts) != 1 || arts[0].EvidenceStatus != EvidenceCorrupt || arts[0].Content != "" {
		t.Fatalf("tampered capture provenance served: %+v err=%v", arts, err)
	}
}
