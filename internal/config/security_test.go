package config

import (
	"github.com/spf13/viper"
	"testing"
)

func TestAPIKeyBindsDocumentedEnvironment(t *testing.T) {
	viper.Reset()
	t.Cleanup(viper.Reset)
	t.Setenv("API_KEY", "environment-test-secret")
	cfg, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Auth.APIKey != "environment-test-secret" {
		t.Fatalf("API_KEY not loaded: %q", cfg.Auth.APIKey)
	}
}
func TestDefaultConfigurationHasNoCredentialsOrWildcardOrigins(t *testing.T) {
	viper.Reset()
	t.Cleanup(viper.Reset)
	t.Setenv("API_KEY", "")
	t.Setenv("AUTH_API_KEY", "")
	cfg, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Auth.APIKey != "" {
		t.Fatal("default API key must be empty")
	}
	for _, origin := range cfg.Server.AllowedOrigins {
		if origin == "*" {
			t.Fatal("default origin must not be wildcard")
		}
	}
}
