package models

import (
	"encoding/json"
	"testing"
)

func TestGRCConfigOmittedOutputDefaultsToPythonLimit(t *testing.T) {
	for _, input := range []string{`{}`, `{"model":"openrouter/vendor/model:free"}`} {
		var config GRCAnalysisConfig
		if err := json.Unmarshal([]byte(input), &config); err != nil {
			t.Fatal(err)
		}
		if config.MaxTokens != 16000 {
			t.Fatalf("omitted max_tokens became %d, want 16000", config.MaxTokens)
		}
	}
}

func TestGRCConfigExplicitInvalidOutputIsRejected(t *testing.T) {
	for _, value := range []string{"0", "-1", "16001", "true", "false", "8000.0", `"8000"`, "null"} {
		t.Run(value, func(t *testing.T) {
			var config GRCAnalysisConfig
			if err := json.Unmarshal([]byte(`{"max_tokens":`+value+`}`), &config); err == nil {
				t.Fatal("explicit invalid max_tokens was accepted")
			}
		})
	}
}

func TestGRCConfigProgrammaticSerializationPreservesDefaultAndCap(t *testing.T) {
	for _, cap := range []int{0, 1, 16000} {
		data, err := json.Marshal(GRCAnalysisConfig{MaxTokens: cap})
		if err != nil {
			t.Fatal(err)
		}
		var value map[string]any
		if err := json.Unmarshal(data, &value); err != nil {
			t.Fatal(err)
		}
		expected := cap
		if expected == 0 {
			expected = 16000
		}
		if value["max_tokens"] != float64(expected) {
			t.Fatalf("serialized allowance %v, want %d", value["max_tokens"], expected)
		}
	}
	for _, cap := range []int{-1, 16001} {
		if _, err := json.Marshal(GRCAnalysisConfig{MaxTokens: cap}); err == nil {
			t.Fatal("out-of-policy programmatic allowance was serialized")
		}
	}
}
