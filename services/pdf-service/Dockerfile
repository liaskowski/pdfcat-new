FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache build-base

# Copy go mod files
COPY go.mod ./
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -o pdf-processing .

# Use minimal runtime image
FROM alpine:latest

WORKDIR /app

# Copy binary
COPY --from=builder /app/pdf-processing .

# Create data directory
RUN mkdir -p data

EXPOSE 8002

CMD ["./pdf-processing"]
