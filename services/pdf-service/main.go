package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// Job represents a PDF processing job
type Job struct {
	ID        string    `json:"id"`
	Type      string    `json:"type"` // "extract", "preview", "optimize"
	Status    string    `json:"status"` // "pending", "processing", "completed", "failed"
	CreatedAt time.Time `json:"created_at"`
	StartedAt *time.Time `json:"started_at,omitempty"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`
	Result    interface{} `json:"result,omitempty"`
	Error     string     `json:"error,omitempty"`
}

// JobManager manages concurrent PDF processing jobs
type JobManager struct {
	jobs    map[string]*Job
	jobsMux sync.RWMutex
	queue   chan *Job
	workers int
}

// Global job manager
var jobManager = &JobManager{
	jobs:    make(map[string]*Job),
	queue:   make(chan *Job, 100),
	workers: 10,
}

func (jm *JobManager) Start() {
	for i := 0; i < jm.workers; i++ {
		go jm.worker()
	}
	log.Printf("Started %d PDF processing workers", jm.workers)
}

func (jm *JobManager) worker() {
	for job := range jm.queue {
		jm.processJob(job)
	}
}

func (jm *JobManager) processJob(job *Job) {
	jm.jobsMux.Lock()
	job.Status = "processing"
	now := time.Now()
	job.StartedAt = &now
	jm.jobs[job.ID] = job
	jm.jobsMux.Unlock()

	// Simulate processing time (500ms for demo)
	time.Sleep(500 * time.Millisecond)

	// Mock result based on job type
	var result interface{}
	switch job.Type {
	case "extract":
		result = map[string]interface{}{
			"text":     "Mock extracted text from PDF document...",
			"pages":    10,
			"metadata": map[string]string{
				"title":  "Sample PDF Document",
				"author": "Test Author",
			},
		}
	case "preview":
		result = map[string]interface{}{
			"image_data": "mock-preview-image-data",
			"width":     200,
			"height":    200,
			"page":      1,
		}
	case "optimize":
		result = map[string]interface{}{
			"original_size":    1024000,
			"optimized_size":   512000,
			"compression_ratio": 0.5,
		}
	}

	// Update job status
	jm.jobsMux.Lock()
	completedAt := time.Now()
	job.CompletedAt = &completedAt
	job.Status = "completed"
	job.Result = result
	jm.jobs[job.ID] = job
	jm.jobsMux.Unlock()
}

func (jm *JobManager) AddJob(jobType string, jobID string) *Job {
	job := &Job{
		ID:        jobID,
		Type:      jobType,
		Status:    "pending",
		CreatedAt: time.Now(),
	}

	jm.jobsMux.Lock()
	jm.jobs[jobID] = job
	jm.jobsMux.Unlock()

	// Add to queue
	select {
	case jm.queue <- job:
		log.Printf("Job %s added to queue", jobID)
	default:
		log.Printf("Queue full, job %s rejected", jobID)
		job.Status = "failed"
		job.Error = "Queue full"
	}

	return job
}

func (jm *JobManager) GetJob(jobID string) *Job {
	jm.jobsMux.RLock()
	defer jm.jobsMux.RUnlock()
	return jm.jobs[jobID]
}

// HTTP Handlers
func handleExtractText(c *gin.Context) {
	documentID := c.PostForm("document_id")
	if documentID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "document_id required"})
		return
	}

	jobID := fmt.Sprintf("extract_%s_%d", documentID, time.Now().Unix())
	jobManager.AddJob("extract", jobID)

	c.JSON(http.StatusOK, gin.H{
		"job_id": jobID,
		"status": "pending",
	})
}

func handleGeneratePreview(c *gin.Context) {
	documentID := c.PostForm("document_id")
	page := c.DefaultPostForm("page", "1")
	width := c.DefaultPostForm("width", "200")

	if documentID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "document_id required"})
		return
	}

	jobID := fmt.Sprintf("preview_%s_%s_%s", documentID, page, width)
	jobManager.AddJob("preview", jobID)

	c.JSON(http.StatusOK, gin.H{
		"job_id": jobID,
		"status": "pending",
	})
}

func handleOptimizePDF(c *gin.Context) {
	documentID := c.PostForm("document_id")
	if documentID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "document_id required"})
		return
	}

	jobID := fmt.Sprintf("optimize_%s_%d", documentID, time.Now().Unix())
	jobManager.AddJob("optimize", jobID)

	c.JSON(http.StatusOK, gin.H{
		"job_id": jobID,
		"status": "pending",
	})
}

func handleJobStatus(c *gin.Context) {
	jobID := c.Param("job_id")
	if jobID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "job_id required"})
		return
	}

	job := jobManager.GetJob(jobID)
	if job == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "job not found"})
		return
	}

	c.JSON(http.StatusOK, job)
}

func handleHealth(c *gin.Context) {
	jobManager.jobsMux.RLock()
	pending := 0
	processing := 0
	completed := 0
	failed := 0

	for _, job := range jobManager.jobs {
		switch job.Status {
		case "pending":
			pending++
		case "processing":
			processing++
		case "completed":
			completed++
		case "failed":
			failed++
		}
	}
	jobManager.jobsMux.RUnlock()

	c.JSON(http.StatusOK, gin.H{
		"status": "healthy",
		"service": "PDF Processing Service",
		"version": "1.0.0",
		"jobs": gin.H{
			"pending":    pending,
			"processing": processing,
			"completed": completed,
			"failed":    failed,
		},
		"workers": jobManager.workers,
	})
}

func handleStats(c *gin.Context) {
	jobManager.jobsMux.RLock()
	totalJobs := len(jobManager.jobs)
	queueLength := len(jobManager.queue)
	jobManager.jobsMux.RUnlock()

	c.JSON(http.StatusOK, gin.H{
		"total_jobs":    totalJobs,
		"queue_length":  queueLength,
		"workers":       jobManager.workers,
		"uptime":        "0s", // Would track actual start time
	})
}

func main() {
	// Start job manager
	jobManager.Start()

	// Gin setup
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()

	// Middleware
	r.Use(gin.Recovery())
	r.Use(func(c *gin.Context) {
		c.Header("Service", "PDF-Processing")
		c.Next()
	})

	// Routes
	r.GET("/health", handleHealth)
	r.GET("/stats", handleStats)
	r.POST("/extract", handleExtractText)
	r.POST("/preview", handleGeneratePreview)
	r.POST("/optimize", handleOptimizePDF)
	r.GET("/job/:job_id", handleJobStatus)

	// Server configuration
	port := os.Getenv("PORT")
	if port == "" {
		port = "8002"
	}

	fmt.Printf("🚀 PDF Processing Service starting on port %s\n", port)
	fmt.Printf("👥 Workers: %d\n", jobManager.workers)
	fmt.Printf("📊 Queue capacity: %d\n", cap(jobManager.queue))

	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
