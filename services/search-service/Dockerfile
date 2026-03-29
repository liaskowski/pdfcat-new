FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache build-base

# Copy go mod and sum files
COPY go.mod ./
# If go.sum existed, I'd copy it too. Let's run go mod tidy later if needed.
RUN go mod download

# Copy the source code
COPY . .

# Build the application
RUN go build -o search-service .

# Use a small alpine image for the final stage
FROM alpine:latest

WORKDIR /app

# Copy the binary from the builder stage
COPY --from=builder /app/search-service .

# Create directory for index data
RUN mkdir -p data

EXPOSE 8001

CMD ["./search-service"]
