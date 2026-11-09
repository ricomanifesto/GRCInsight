package dynamodb

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
)

// API is the subset of the DynamoDB client the repository uses.
type API interface {
	GetItem(context.Context, *dynamodb.GetItemInput, ...func(*dynamodb.Options)) (*dynamodb.GetItemOutput, error)
	PutItem(context.Context, *dynamodb.PutItemInput, ...func(*dynamodb.Options)) (*dynamodb.PutItemOutput, error)
	UpdateItem(context.Context, *dynamodb.UpdateItemInput, ...func(*dynamodb.Options)) (*dynamodb.UpdateItemOutput, error)
	DeleteItem(context.Context, *dynamodb.DeleteItemInput, ...func(*dynamodb.Options)) (*dynamodb.DeleteItemOutput, error)
	Query(context.Context, *dynamodb.QueryInput, ...func(*dynamodb.Options)) (*dynamodb.QueryOutput, error)
	Scan(context.Context, *dynamodb.ScanInput, ...func(*dynamodb.Options)) (*dynamodb.ScanOutput, error)
	DescribeTable(context.Context, *dynamodb.DescribeTableInput, ...func(*dynamodb.Options)) (*dynamodb.DescribeTableOutput, error)
}

var _ API = (*dynamodb.Client)(nil)

// History record kinds written by the report writer.
const (
	RecordKindRevision   = "article_revision"
	RecordKindAppearance = "report_article_appearance"

	// OutcomeGuard is present once a report has a final, digest-bound outcome.
	OutcomeGuard = "outcome_sha256"

	// MaxReportArticles bounds how many article rows one report listing reads.
	MaxReportArticles = 1000
	queryPageLimit    = 100
)

// Evidence states reported for each article returned by a report listing.
const (
	EvidenceIntact  = "intact"
	EvidenceMissing = "missing"
	EvidenceCorrupt = "corrupt"
	EvidenceUnbound = "unbound"
	EvidenceLegacy  = "legacy"
)

// ErrReportFinal means a report already has a final outcome and was not changed.
var ErrReportFinal = errors.New("report outcome is final")

// pythonJSONString encodes s exactly as Python's json.dumps(ensure_ascii=False) does.
func pythonJSONString(b *strings.Builder, s string) {
	b.WriteByte('"')
	for _, r := range s {
		switch r {
		case '"':
			b.WriteString(`\"`)
		case '\\':
			b.WriteString(`\\`)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		case '\b':
			b.WriteString(`\b`)
		case '\f':
			b.WriteString(`\f`)
		default:
			if r < 0x20 {
				fmt.Fprintf(b, `\u%04x`, r)
			} else {
				b.WriteRune(r)
			}
		}
	}
	b.WriteByte('"')
}

// RevisionDigest is the SHA-256 of a revision's retained fields in canonical JSON.
func RevisionDigest(url, title, summary, content string) (string, bool) {
	for _, v := range []string{url, title, summary, content} {
		if !utf8.ValidString(v) {
			return "", false
		}
	}
	var b strings.Builder
	// Canonical JSON sorts keys: content, summary, title, url.
	b.WriteString(`{"content":`)
	pythonJSONString(&b, content)
	b.WriteString(`,"summary":`)
	pythonJSONString(&b, summary)
	b.WriteString(`,"title":`)
	pythonJSONString(&b, title)
	b.WriteString(`,"url":`)
	pythonJSONString(&b, url)
	b.WriteByte('}')
	sum := sha256.Sum256([]byte(b.String()))
	return hex.EncodeToString(sum[:]), true
}

// verifyRevision re-derives a stored revision's identity from its retained text.
func verifyRevision(rev *Article, expectedDigest string) bool {
	digest, ok := RevisionDigest(rev.URL, rev.Title, rev.Summary, rev.Content)
	if !ok || len(digest) < 32 {
		return false
	}
	return rev.RecordKind == RecordKindRevision &&
		rev.ContentSHA256 == digest &&
		expectedDigest == digest &&
		strings.HasSuffix(rev.ArticleID, "#"+digest[:32])
}

// queryReportRows reads up to MaxReportArticles article rows for a report.
func (r *Repository) queryReportRows(ctx context.Context, reportID string) ([]Article, error) {
	var rows []Article
	var start map[string]types.AttributeValue
	for {
		out, err := r.client.Query(ctx, &dynamodb.QueryInput{
			TableName:              aws.String(ArticlesTable),
			IndexName:              aws.String(ArticlesByReport),
			KeyConditionExpression: aws.String("report_id = :rid"),
			ExpressionAttributeValues: map[string]types.AttributeValue{
				":rid": &types.AttributeValueMemberS{Value: reportID},
			},
			ExclusiveStartKey: start,
			Limit:             aws.Int32(queryPageLimit),
		})
		if err != nil {
			return nil, fmt.Errorf("failed to query report articles: %w", err)
		}
		for _, item := range out.Items {
			var a Article
			if err := attributevalue.UnmarshalMap(item, &a); err == nil {
				rows = append(rows, a)
			}
		}
		if len(rows) >= MaxReportArticles {
			return rows[:MaxReportArticles], nil
		}
		if len(out.LastEvaluatedKey) == 0 {
			return rows, nil
		}
		start = out.LastEvaluatedKey
	}
}

// fetchRevisions reads the revisions one page references with strongly consistent
// GetItem calls (the deployed role grants GetItem, not BatchGetItem). The caller's
// page size bounds the number of reads; absent ids are omitted.
func (r *Repository) fetchRevisions(ctx context.Context, ids []string) (map[string]*Article, error) {
	found := make(map[string]*Article, len(ids))
	for _, id := range ids {
		if _, seen := found[id]; seen {
			continue
		}
		out, err := r.client.GetItem(ctx, &dynamodb.GetItemInput{
			TableName:      aws.String(ArticlesTable),
			Key:            map[string]types.AttributeValue{"article_id": &types.AttributeValueMemberS{Value: id}},
			ConsistentRead: aws.Bool(true),
		})
		if err != nil {
			return nil, fmt.Errorf("failed to read article revision: %w", err)
		}
		if out.Item == nil {
			continue
		}
		var rev Article
		if err := attributevalue.UnmarshalMap(out.Item, &rev); err == nil {
			found[id] = &rev
		}
	}
	return found, nil
}

// ReportArticles lists one report's articles with bounded paging.
//
// Legacy rows are returned as stored. History appearances are filtered to the
// set the report's final outcome binds, ordered by position, and their text is
// read from the referenced revision only when that revision verifies.
func (r *Repository) ReportArticles(ctx context.Context, reportID string, limit, offset int32) ([]Article, int64, error) {
	// An unknown report lists no bound appearances, as the listing did before history.
	out, err := r.client.GetItem(ctx, &dynamodb.GetItemInput{
		TableName: aws.String(TableName),
		Key:       map[string]types.AttributeValue{"report_id": &types.AttributeValueMemberS{Value: reportID}},
	})
	if err != nil {
		return nil, 0, fmt.Errorf("failed to read report: %w", err)
	}
	var report Report
	if out.Item != nil {
		if err := attributevalue.UnmarshalMap(out.Item, &report); err != nil {
			return nil, 0, fmt.Errorf("failed to unmarshal report: %w", err)
		}
	}
	rows, err := r.queryReportRows(ctx, reportID)
	if err != nil {
		return nil, 0, err
	}

	var legacy, bound, unbound []Article
	for _, row := range rows {
		switch row.RecordKind {
		case "":
			row.EvidenceStatus = EvidenceLegacy
			legacy = append(legacy, row)
		case RecordKindAppearance:
			if report.AppearanceSet != "" && row.AppearanceSet == report.AppearanceSet {
				bound = append(bound, row)
			} else {
				row.EvidenceStatus = EvidenceUnbound
				unbound = append(unbound, row)
			}
		}
	}
	listed := legacy
	if report.AppearanceSet != "" {
		sort.SliceStable(bound, func(i, j int) bool { return bound[i].Position < bound[j].Position })
		listed = append(listed, bound...)
	} else {
		// Without a final outcome nothing is bound; show what exists, labelled as unbound.
		sort.SliceStable(unbound, func(i, j int) bool { return unbound[i].Position < unbound[j].Position })
		listed = append(listed, unbound...)
	}

	total := int64(len(listed))
	if int(offset) >= len(listed) {
		return []Article{}, total, nil
	}
	page := listed[offset:]
	if int(limit) < len(page) {
		page = page[:limit]
	}
	page = append([]Article(nil), page...)

	var ids []string
	for _, a := range page {
		if a.RecordKind == RecordKindAppearance && a.RevisionID != "" {
			ids = append(ids, a.RevisionID)
		}
	}
	revisions, err := r.fetchRevisions(ctx, ids)
	if err != nil {
		return nil, 0, err
	}
	for i := range page {
		a := &page[i]
		if a.RecordKind != RecordKindAppearance {
			continue
		}
		rev, ok := revisions[a.RevisionID]
		switch {
		case !ok:
			if a.EvidenceStatus == "" {
				a.EvidenceStatus = EvidenceMissing
			}
		case !verifyRevision(rev, a.ContentSHA256):
			a.EvidenceStatus = EvidenceCorrupt
		default:
			if a.EvidenceStatus == "" {
				a.EvidenceStatus = EvidenceIntact
			}
			a.Content = rev.Content
			a.Summary = rev.Summary
			a.PublishedAt = rev.PublishedAt
			a.PublishedAtKnown = rev.PublishedAtKnown
		}
	}
	return page, total, nil
}

// openReportCondition admits a write only while a report is open and has no final outcome.
func openReportCondition(values map[string]types.AttributeValue, names map[string]string) string {
	values[":pending"] = &types.AttributeValueMemberS{Value: StatusPending}
	values[":processing"] = &types.AttributeValueMemberS{Value: StatusProcessing}
	names["#status"] = "status"
	names["#guard"] = OutcomeGuard
	return "attribute_exists(report_id) AND #status IN (:pending, :processing) AND attribute_not_exists(#guard)"
}

func isConditionFailure(err error) bool {
	var ccf *types.ConditionalCheckFailedException
	return errors.As(err, &ccf)
}

// MarkReportFailedIfOpen records a failure the Go service observed (for example a
// failed invocation) without ever overwriting a final outcome.
func (r *Repository) MarkReportFailedIfOpen(ctx context.Context, reportID, reason string) error {
	values := map[string]types.AttributeValue{
		":failed":     &types.AttributeValueMemberS{Value: StatusFailed},
		":outcome":    &types.AttributeValueMemberS{Value: "failed"},
		":reason":     &types.AttributeValueMemberS{Value: reason},
		":updated_at": &types.AttributeValueMemberS{Value: ToISO8601(nowFunc())},
	}
	names := map[string]string{}
	condition := openReportCondition(values, names)
	_, err := r.client.UpdateItem(ctx, &dynamodb.UpdateItemInput{
		TableName:                 aws.String(TableName),
		Key:                       map[string]types.AttributeValue{"report_id": &types.AttributeValueMemberS{Value: reportID}},
		UpdateExpression:          aws.String("SET #status = :failed, terminal_outcome = :outcome, terminal_reason = :reason, updated_at = :updated_at"),
		ConditionExpression:       aws.String(condition),
		ExpressionAttributeNames:  names,
		ExpressionAttributeValues: values,
	})
	if isConditionFailure(err) {
		return ErrReportFinal
	}
	if err != nil {
		return fmt.Errorf("failed to mark report failed: %w", err)
	}
	return nil
}
