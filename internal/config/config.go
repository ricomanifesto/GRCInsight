package config

import (
	"strings"
	"time"

	"github.com/spf13/viper"
)

// Config represents the application configuration
type Config struct {
	Server        ServerConfig        `mapstructure:"server"`
	Database      DatabaseConfig      `mapstructure:"database"`
	PythonService PythonServiceConfig `mapstructure:"python_service"`
	Logging       LoggingConfig       `mapstructure:"logging"`
	Auth          AuthConfig          `mapstructure:"auth"`
}

// ServerConfig holds server-related configuration
type ServerConfig struct {
    Port int    `mapstructure:"port"`
    Mode string `mapstructure:"mode"`
    Host string `mapstructure:"host"`
    AllowedOrigins []string `mapstructure:"allowed_origins"`
}

// DatabaseConfig holds DynamoDB configuration
type DatabaseConfig struct {
	Region   string `mapstructure:"region"`
	Endpoint string `mapstructure:"endpoint"`
}

// PythonServiceConfig holds Python service configuration
type PythonServiceConfig struct {
    URL     string        `mapstructure:"url"`
    Timeout time.Duration `mapstructure:"timeout"`
    // Optional: when set, forces Lambda invocation mode with this function name
    LambdaFunctionName string `mapstructure:"lambda_function_name"`
    InvokeAsync       bool          `mapstructure:"invoke_async"`
}

// LoggingConfig holds logging configuration
type LoggingConfig struct {
	Level  string `mapstructure:"level"`
	Format string `mapstructure:"format"`
}

// AuthConfig holds authentication configuration
type AuthConfig struct {
	JWTSecret string `mapstructure:"jwt_secret"`
	APIKey    string `mapstructure:"api_key"`
}

// Load loads configuration from file and environment variables
func Load() (*Config, error) {
	// Set default values
    viper.SetDefault("server.port", 8080)
    viper.SetDefault("server.mode", "release")
    viper.SetDefault("server.host", "0.0.0.0")
    viper.SetDefault("server.allowed_origins", []string{"*"})
	viper.SetDefault("database.region", "us-east-1")
	viper.SetDefault("database.endpoint", "")
    viper.SetDefault("python_service.url", "http://localhost:8081")
    viper.SetDefault("python_service.timeout", "300s")
    viper.SetDefault("python_service.lambda_function_name", "")
    viper.SetDefault("python_service.invoke_async", false)
	viper.SetDefault("logging.level", "info")
	viper.SetDefault("logging.format", "text")

	// Configuration file settings
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./configs")
	viper.AddConfigPath(".")

	// Environment variables
	viper.AutomaticEnv()
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	// Read configuration file (optional)
	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, err
		}
	}

	// Override with environment-specific config if available
	env := viper.GetString("GO_ENV")
	if env != "" {
		viper.SetConfigName("config." + env)
		if err := viper.MergeInConfig(); err != nil {
			if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
				return nil, err
			}
		}
	}

	var config Config
	if err := viper.Unmarshal(&config); err != nil {
		return nil, err
	}

	return &config, nil
}
