FROM golang:1.21-alpine AS builder

# Set working directory
WORKDIR /app

# Install git (needed for Go modules)
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o main cmd/server/main.go

# Final stage
FROM alpine:latest

# Install ca-certificates for HTTPS calls
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/main .

# Copy configuration files
COPY --from=builder /app/configs ./configs
COPY --from=builder /app/site ./site

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8080

# Run the application
CMD ["./main"]