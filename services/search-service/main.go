package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"
)

// --- 1. Models ---

type IndexRequest struct {
	ID      int    `json:"id" binding:"required"`
	Content string `json:"content" binding:"required"`
}

type SearchResult struct {
	ID    int     `json:"id"`
	Score float64 `json:"score"`
}

// --- 2. Simple In-Memory Index ---

type DocumentIndex struct {
	mu        sync.RWMutex
	documents map[int]string // id -> content
}

var index = &DocumentIndex{
	documents: make(map[int]string),
}

// --- 3. Handlers ---

func handleIndex(c *gin.Context) {
	var req IndexRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	index.mu.Lock()
	index.documents[req.ID] = req.Content
	index.mu.Unlock()

	c.JSON(http.StatusOK, gin.H{"status": "indexed", "id": req.ID})
}

func handleSearch(c *gin.Context) {
	queryStr := c.Query("q")
	if queryStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Query parameter 'q' is required"})
		return
	}

	index.mu.RLock()
	defer index.mu.RUnlock()

	var results []SearchResult
	queryLower := strings.ToLower(queryStr)

	for id, content := range index.documents {
		contentLower := strings.ToLower(content)
		if strings.Contains(contentLower, queryLower) {
			// Simple scoring based on occurrences
			score := float64(strings.Count(contentLower, queryLower))
			results = append(results, SearchResult{
				ID:    id,
				Score: score,
			})
		}
	}

	c.JSON(http.StatusOK, results)
}

func handleDelete(c *gin.Context) {
	idStr := c.Param("id")
	if idStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "ID is required"})
		return
	}

	id, err := strconv.Atoi(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
		return
	}

	index.mu.Lock()
	delete(index.documents, id)
	index.mu.Unlock()

	c.JSON(http.StatusOK, gin.H{"status": "deleted", "id": id})
}

func handleHealth(c *gin.Context) {
	index.mu.RLock()
	docCount := len(index.documents)
	index.mu.RUnlock()

	c.JSON(http.StatusOK, gin.H{
		"status":    "healthy",
		"service":   "Search Service",
		"version":   "1.0.0",
		"documents": docCount,
	})
}

// --- 4. Main ---

func main() {
	r := gin.Default()

	// Middleware
	r.Use(gin.Recovery())
	r.Use(func(c *gin.Context) {
		c.Header("Service", "Search-Service")
		c.Next()
	})

	// Routes
	r.GET("/health", handleHealth)
	r.POST("/index", handleIndex)
	r.GET("/search", handleSearch)
	r.DELETE("/index/:id", handleDelete)

	// Server configuration
	port := os.Getenv("PORT")
	if port == "" {
		port = "8001"
	}

	fmt.Printf("🔍 Search Service starting on port %s\n", port)
	fmt.Printf("📊 Simple in-memory search engine (no Bluge dependencies)\n")

	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Server Run Error: %v", err)
	}
}
