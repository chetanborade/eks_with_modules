provider "aws" {
  region = "ap-south-1"
}

# ECR Repository for Frontend
resource "aws_ecr_repository" "frontend" {
  name = "tictactoe-frontend"
}

# ECR Repository for Backend  
resource "aws_ecr_repository" "backend" {
  name = "tictactoe-backend"
}

# ECR Repository for Game Engine
resource "aws_ecr_repository" "game_engine" {
  name = "tictactoe-game-engine"
}

# Show the URLs after creation
output "frontend_ecr_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "backend_ecr_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "game_engine_ecr_url" {
  value = aws_ecr_repository.game_engine.repository_url
}