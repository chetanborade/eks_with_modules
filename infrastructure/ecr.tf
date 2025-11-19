# ECR repositories for microservices
resource "aws_ecr_repository" "tictactoe_frontend" {
  name = "tictactoe-frontend"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = {
    Name        = "TicTacToe Frontend ECR"
    Environment = "dev"
    Terraform   = "true"
  }
}

resource "aws_ecr_repository" "tictactoe_backend" {
  name = "tictactoe-backend"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = {
    Name        = "TicTacToe Backend ECR"
    Environment = "dev"
    Terraform   = "true"
  }
}

resource "aws_ecr_repository" "tictactoe_game_engine" {
  name = "tictactoe-game-engine"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = {
    Name        = "TicTacToe Game Engine ECR"
    Environment = "dev"
    Terraform   = "true"
  }
}

# Output ECR URLs for GitHub Actions
output "ecr_repositories" {
  value = {
    frontend    = aws_ecr_repository.tictactoe_frontend.repository_url
    backend     = aws_ecr_repository.tictactoe_backend.repository_url
    game_engine = aws_ecr_repository.tictactoe_game_engine.repository_url
  }
  description = "ECR repository URLs for CI/CD"
}