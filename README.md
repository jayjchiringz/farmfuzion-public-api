# FarmFuzion Global Marketplace API

Public API for bulk agricultural produce sales at cooperative and international levels.

## API Documentation

Once deployed, visit:
- Swagger UI: `https://farmfuzion-public-api.onrender.com/docs`
- ReDoc: `https://farmfuzion-public-api.onrender.com/redoc`

## Deployment on Render

1. Push this repository to GitHub
2. On Render, click "New +" → "Web Service"
3. Connect to your GitHub repository
4. Render will automatically detect the `render.yaml` file
5. Click "Apply" to deploy

## Environment Variables

The following variables are automatically set by Render:
- `DATABASE_URL`: PostgreSQL connection string
- `PUBLIC_API_KEY`: Generated API key for authentication
- `CORS_ORIGINS`: Allowed origins for CORS

## Testing

```bash
# Health check
curl https://farmfuzion-public-api.onrender.com/

# List products
curl https://farmfuzion-public-api.onrender.com/api/v1/products

# Get marketplace stats
curl https://farmfuzion-public-api.onrender.com/api/v1/stats