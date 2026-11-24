FROM golang:1.27.4-alpine3.23@sha256:f70850ef6ce341e8b6427f677049145d63c0b7ce002d4d7e3d464828b1b96dcd AS builder

# Set working directory
WORKDIR /app

# Install git (needed for Go modules)
RUN apk add --no-cache git gcc musl-dev

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o main cmd/server/main.go

# Final stage
FROM alpine:3.23@sha256:469c9ea410b9215eaee7976ba6c0639039b444be8e5d638f7abbada189971eb2

# Install ca-certificates for HTTPS calls
RUN apk --no-cache add ca-certificates

RUN addgroup -S -g 10001 app && adduser -S -D -u 10001 -G app app

WORKDIR /app

# Copy the binary from builder stage
COPY --from=builder /app/main .

# Copy configuration files
COPY --from=builder /app/configs ./configs
COPY --from=builder /app/site ./site

# Create data directory
RUN mkdir -p data && chown -R app:app /app
USER 10001:10001

# Expose port
EXPOSE 8080

# Run the application
CMD ["./main"]
