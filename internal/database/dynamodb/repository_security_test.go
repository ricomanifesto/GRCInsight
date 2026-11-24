package dynamodb

import (
	"context"
	"errors"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/sirupsen/logrus"
	"io"
	"testing"
)

type policyAPI struct {
	*fakeAPI
	pages   []*dynamodb.ScanOutput
	scans   int
	scanErr error
}

func (f *policyAPI) Scan(_ context.Context, in *dynamodb.ScanInput, _ ...func(*dynamodb.Options)) (*dynamodb.ScanOutput, error) {
	f.scans++
	if f.scanErr != nil {
		return nil, f.scanErr
	}
	if f.scans > 1 && len(in.ExclusiveStartKey) == 0 {
		return nil, errors.New("missing continuation key")
	}
	if len(f.pages) == 0 {
		return &dynamodb.ScanOutput{}, nil
	}
	page := f.pages[0]
	f.pages = f.pages[1:]
	return page, nil
}
func (f *policyAPI) DeleteItem(_ context.Context, in *dynamodb.DeleteItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.DeleteItemOutput, error) {
	id := str(in.Key["report_id"])
	item, exists := f.tables[TableName][id]
	if !exists {
		return nil, &types.ConditionalCheckFailedException{}
	}
	if aws.ToString(in.ConditionExpression) == "attribute_exists(report_id) AND #status IN (:pending, :processing) AND attribute_not_exists(#guard)" {
		_, guard := item[OutcomeGuard]
		status := str(item[in.ExpressionAttributeNames["#status"]])
		if guard || (status != StatusPending && status != StatusProcessing) {
			return nil, &types.ConditionalCheckFailedException{}
		}
	}
	delete(f.tables[TableName], id)
	return &dynamodb.DeleteItemOutput{}, nil
}
func securityRepo(api *policyAPI) *Repository {
	logger := logrus.New()
	logger.SetOutput(io.Discard)
	return NewRepository(api, logger)
}
func pageKey() map[string]types.AttributeValue {
	return map[string]types.AttributeValue{"article_id": &types.AttributeValueMemberS{Value: "page-marker"}}
}
func articleItem(id string) map[string]types.AttributeValue {
	return map[string]types.AttributeValue{"article_id": &types.AttributeValueMemberS{Value: id}, "url": &types.AttributeValueMemberS{Value: "https://example.test/" + id}}
}
func TestFilteredArticleLookupsFollowEmptyPages(t *testing.T) {
	for _, kind := range []string{"numeric", "url"} {
		t.Run(kind, func(t *testing.T) {
			api := &policyAPI{fakeAPI: newFakeAPI(), pages: []*dynamodb.ScanOutput{{LastEvaluatedKey: pageKey()}, {Items: []map[string]types.AttributeValue{articleItem("target")}}}}
			repo := securityRepo(api)
			var art *Article
			var err error
			if kind == "numeric" {
				art, err = repo.GetArticleByNumericID(context.Background(), 42)
			} else {
				art, err = repo.GetArticleByURL(context.Background(), "https://example.test/target")
			}
			if err != nil || art == nil || art.ArticleID != "target" || api.scans != 2 {
				t.Fatalf("later-page match lost: article=%+v scans=%d err=%v", art, api.scans, err)
			}
		})
	}
}
func TestFilteredArticlePaginationCountsMatchesAcrossPages(t *testing.T) {
	api := &policyAPI{fakeAPI: newFakeAPI(), pages: []*dynamodb.ScanOutput{
		{LastEvaluatedKey: pageKey()},
		{Items: []map[string]types.AttributeValue{articleItem("a")}, LastEvaluatedKey: pageKey()},
		{Items: []map[string]types.AttributeValue{articleItem("b"), articleItem("c")}},
	}}
	arts, err := securityRepo(api).GetGRCArticles(context.Background(), 2, 1)
	if err != nil || len(arts) != 2 || arts[0].ArticleID != "b" || arts[1].ArticleID != "c" || api.scans != 3 {
		t.Fatalf("match pagination: %+v scans=%d err=%v", arts, api.scans, err)
	}
}
func TestFilteredLookupStopsAtExhaustionAndPropagatesErrors(t *testing.T) {
	api := &policyAPI{fakeAPI: newFakeAPI(), pages: []*dynamodb.ScanOutput{{LastEvaluatedKey: pageKey()}, {}}}
	if _, err := securityRepo(api).GetArticleByURL(context.Background(), "https://example.test/missing"); err == nil || api.scans != 2 {
		t.Fatalf("not found: scans=%d err=%v", api.scans, err)
	}
	api = &policyAPI{fakeAPI: newFakeAPI(), scanErr: context.Canceled}
	if _, err := securityRepo(api).GetArticleByNumericID(context.Background(), 42); !errors.Is(err, context.Canceled) {
		t.Fatalf("scan error swallowed: %v", err)
	}
}
func TestReportDeletePreservesFinalAndLegacyTerminalRows(t *testing.T) {
	for _, tc := range []struct {
		status  string
		guard   bool
		blocked bool
	}{{StatusCompleted, true, true}, {StatusCompleted, false, true}, {StatusFailed, false, true}, {StatusProcessing, true, true}, {StatusProcessing, false, false}, {StatusPending, false, false}} {
		t.Run(tc.status+map[bool]string{true: "-guard", false: ""}[tc.guard], func(t *testing.T) {
			api := &policyAPI{fakeAPI: newFakeAPI()}
			item := map[string]types.AttributeValue{"report_id": &types.AttributeValueMemberS{Value: "r"}, "status": &types.AttributeValueMemberS{Value: tc.status}}
			if tc.guard {
				item[OutcomeGuard] = &types.AttributeValueMemberS{Value: "test-digest"}
			}
			api.put(TableName, item)
			err := securityRepo(api).DeleteReport(context.Background(), "r")
			_, present := api.tables[TableName]["r"]
			if tc.blocked && (!errors.Is(err, ErrReportFinal) || !present) {
				t.Fatalf("final row deleted: present=%t err=%v", present, err)
			}
			if !tc.blocked && (err != nil || present) {
				t.Fatalf("open delete failed: present=%t err=%v", present, err)
			}
		})
	}
}
