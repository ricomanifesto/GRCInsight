package main

import (
	"net/http"
	"testing"
	"time"
)

func TestHTTPServerHasBoundedConnectionLifetimes(t *testing.T) {
	s := newHTTPServer("127.0.0.1:8080", http.NewServeMux())
	if s.ReadHeaderTimeout <= 0 || s.ReadTimeout <= 0 || s.WriteTimeout <= 0 || s.IdleTimeout <= 0 {
		t.Fatalf("unbounded timeouts: %+v", s)
	}
	if s.WriteTimeout <= 5*time.Minute {
		t.Fatal("write timeout must accommodate the 300s synchronous workflow")
	}
	if s.Addr != "127.0.0.1:8080" || s.Handler == nil {
		t.Fatal("server lost listener/handler")
	}
}
