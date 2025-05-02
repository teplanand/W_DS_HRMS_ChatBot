# API Documentation

## POST /chat
**Description**: Sends a query to the chatbot and streams a response.

**Request**:
```json
{
    "question": "What's the leave policy?"
}
```

**Response**:
```json
{
    "answer": "The leave policy includes..."
}
```

**Status Codes**:
- 200: Success
- 400: Invalid request
- 500: Server error
