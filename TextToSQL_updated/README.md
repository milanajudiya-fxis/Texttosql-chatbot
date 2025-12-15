# Text-to-SQL Agent

A production-grade Text-to-SQL agent that translates natural language questions into SQL queries using LangChain, LangGraph, and Google's Generative AI.

## Project Structure

```
TextToSQL/
├── src/
│   ├── __init__.py
│   ├── config/              # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py      # Settings dataclasses
│   ├── core/                # Core functionality
│   │   ├── __init__.py
│   │   ├── database.py      # Database manager
│   │   └── llm.py           # LLM manager
│   ├── tools/               # SQL toolkit wrapper
│   │   ├── __init__.py
│   │   └── toolkit.py       # SQL toolkit
│   ├── prompts/             # System prompts
│   │   ├── __init__.py
│   │   └── system_prompts.py
│   └── agents/              # Agent logic
│       ├── __init__.py
│       ├── nodes.py         # Agent node functions
│       └── graph_builder.py # Graph builder
├── tests/                   # Unit tests
│   ├── __init__.py
│   └── test_config.py
├── logs/                    # Application logs
├── main.py                  # Entry point
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
└── README.md                # This file
```

## Features

- **Text-to-SQL Translation**: Convert natural language to SQL queries
- **Query Validation**: Automatic query checking for common mistakes
- **Multi-table Support**: Handle complex queries with joins and aggregations
- **Error Recovery**: Automatic schema retrieval and query correction
- **Production-Ready**: Proper logging, configuration management, and error handling

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd TextToSQL
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Configure the agent using environment variables in `.env`:

```env
# Database Configuration
DB_USER=root
DB_PASSWORD=root
DB_HOST=localhost
DB_PORT=3306
DB_NAME=TextToSQL

# LLM Configuration
LLM_MODEL=gemini-2.0-flash
LLM_TEMPERATURE=0
LLM_MAX_RETRIES=2
GOOGLE_API_KEY=your_api_key_here

# Application Configuration
DEBUG=False
```

## Usage

Run the agent with a natural language question:

```bash
python main.py "What is the total revenue by product?"
```

### Using Docker

You can also run the application using Docker Compose:

1.  **Build and Start**:
    ```bash
    docker-compose up --build
    ```
    This will start the API server on `http://localhost:8010` and a MySQL database.

2.  **Access the API**:
    The API will be available at `http://localhost:8010`. You can check the health status at `http://localhost:8010/health`.

3.  **Stop**:
    ```bash
    docker-compose down
    ```

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Features

1. Create new modules in appropriate `src/` subdirectories
2. Follow the existing structure and naming conventions
3. Add unit tests in `tests/`
4. Update this README with new features

## Architecture

### Configuration (`src/config/`)
- Centralized settings management
- Environment variable support
- Type-safe dataclasses

### Core (`src/core/`)
- `DatabaseManager`: Handles database connections
- `LLMManager`: Manages LLM initialization

### Tools (`src/tools/`)
- `SQLToolkit`: Wrapper for LangChain's SQL toolkit
- Provides access to schema, query execution, and table listing

### Agents (`src/agents/`)
- `AgentNodes`: Individual node functions for the agent
- `AgentGraphBuilder`: Constructs the LangGraph workflow

### Prompts (`src/prompts/`)
- System prompts for query generation and validation
- Dynamic prompt generation based on database dialect

## Logging

The application uses Python's standard logging module. Logs are output to console and can be configured in `main.py`.

## Error Handling

The agent includes built-in error recovery:
- Automatic schema retrieval on column name errors
- Query validation before execution
- Comprehensive error logging

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
