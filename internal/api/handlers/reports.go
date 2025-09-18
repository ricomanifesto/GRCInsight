package handlers

import (
    "net/http"
    "strconv"

    "grcinsight/internal/models"
    "grcinsight/internal/services"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

// ReportsHandler handles report-related endpoints
type ReportsHandler struct {
	reportService *services.ReportService
	logger        *logrus.Logger
}

// NewReportsHandler creates a new reports handler
func NewReportsHandler(reportService *services.ReportService, logger *logrus.Logger) *ReportsHandler {
	return &ReportsHandler{
		reportService: reportService,
		logger:        logger,
	}
}

// GenerateReport generates a new GRC report
func (h *ReportsHandler) GenerateReport(c *gin.Context) {
	var req models.GenerateReportRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		h.logger.WithError(err).Error("Invalid request body")
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request body",
			"details": err.Error(),
		})
		return
	}

	h.logger.WithField("feed_url", req.FeedURL).Info("Generating new report")

	report, err := h.reportService.GenerateReport(&req)
	if err != nil {
		h.logger.WithError(err).Error("Failed to generate report")
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to generate report",
			"details": err.Error(),
		})
		return
	}

    response := models.GenerateReportResponse{
        ReportID: report.ID,
        Status:   report.Status,
        Message:  "Report generation started",
    }

    if report.Status == "completed" {
        response.Message = "Report generated successfully"
    }

    // If still processing (async mode), return 202 Accepted; otherwise 201 Created
    statusCode := http.StatusCreated
    if report.Status == "processing" {
        statusCode = http.StatusAccepted
    }

    c.JSON(statusCode, response)
}

// GetReport retrieves a specific report
func (h *ReportsHandler) GetReport(c *gin.Context) {
    id := c.Param("id")
    report, err := h.reportService.GetReport(id)
    if err != nil {
        h.logger.WithError(err).WithField("report_id", id).Error("Failed to get report")
        c.JSON(http.StatusNotFound, gin.H{
            "error": "Report not found",
        })
        return
    }

	c.JSON(http.StatusOK, report)
}

// ListReports lists all reports with pagination
func (h *ReportsHandler) ListReports(c *gin.Context) {
	// Parse pagination parameters
	page := 1
	perPage := 20

	if pageStr := c.Query("page"); pageStr != "" {
		if p, err := strconv.Atoi(pageStr); err == nil && p > 0 {
			page = p
		}
	}

	if perPageStr := c.Query("per_page"); perPageStr != "" {
		if pp, err := strconv.Atoi(perPageStr); err == nil && pp > 0 && pp <= 100 {
			perPage = pp
		}
	}

	response, err := h.reportService.ListReports(page, perPage)
	if err != nil {
		h.logger.WithError(err).Error("Failed to list reports")
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to list reports",
		})
		return
	}

	c.JSON(http.StatusOK, response)
}

// DeleteReport deletes a specific report
func (h *ReportsHandler) DeleteReport(c *gin.Context) {
    id := c.Param("id")
    if err := h.reportService.DeleteReport(id); err != nil {
        h.logger.WithError(err).WithField("report_id", id).Error("Failed to delete report")
        c.JSON(http.StatusInternalServerError, gin.H{
            "error": "Failed to delete report",
        })
        return
    }

	c.JSON(http.StatusOK, gin.H{
		"message": "Report deleted successfully",
	})
}

// GetReportStatus gets the status of a specific report
func (h *ReportsHandler) GetReportStatus(c *gin.Context) {
    id := c.Param("id")
    report, err := h.reportService.GetReport(id)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{
            "error": "Report not found",
        })
        return
    }

    c.JSON(http.StatusOK, gin.H{
        "id":           report.ID,
        "status":       report.Status,
        "created_at":   report.CreatedAt,
        "generated_at": report.GeneratedAt,
    })
}
