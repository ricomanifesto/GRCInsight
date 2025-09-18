package handlers

import (
	"net/http"
	"path/filepath"

	"github.com/gin-gonic/gin"
)

// StaticHandler handles static file serving
type StaticHandler struct{}

// NewStaticHandler creates a new static handler
func NewStaticHandler() *StaticHandler {
	return &StaticHandler{}
}

// ServeIndex serves the main index.html file
func (h *StaticHandler) ServeIndex(c *gin.Context) {
	c.File("./site/index.html")
}

// ServeStatic serves static assets
func (h *StaticHandler) ServeStatic(c *gin.Context) {
	// Get the requested file path
	requestedPath := c.Param("filepath")
	
	// Construct the full file path
	fullPath := filepath.Join("./site/static", requestedPath)
	
	// Serve the file
	c.File(fullPath)
}

// ServeReport serves generated report files
func (h *StaticHandler) ServeReport(c *gin.Context) {
	reportPath := c.Param("filepath")
	
	// For now, serve the main index.md report
	// In the future, this could serve specific report files
	if reportPath == "index.md" || reportPath == "" {
		c.File("./site/index.md")
		return
	}
	
	c.JSON(http.StatusNotFound, gin.H{
		"error": "Report not found",
	})
}