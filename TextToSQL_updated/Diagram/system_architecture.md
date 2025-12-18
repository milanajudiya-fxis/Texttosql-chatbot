# TextToSQL Project Diagrams

This document contains architectural diagrams for the Text-to-SQL Chatbot project, covering database structure, critical sequence flows, service dependencies, agentic logic, and module features.

## 1. ER Diagram (Conceptual)

Based on the prompt templates and domain context (Sicilian Games 2025-26), the following conceptual Entity-Relationship diagram represents the data model.

```mermaid
erDiagram
    CHAPTER ||--|{ PLAYER : has
    CHAPTER ||--|| STANDINGS : has
    CHAPTER ||--|{ MATCH : participates
    SPORT ||--|{ MATCH : "type of"
    SPORT ||--|{ RULES : "defined by"
    PLAYER }|--|| SPORT : "plays"
    SPONSOR ||--|| EVENT : supports
    
    CHAPTER {
        string name
        string size "Below 40, 40-75, Above 75"
        string coordinator_contact
    }

    PLAYER {
        string name
        string role "Captain, Player"
        string tshirt_size
        string contact_number
        string email
    }

    MATCH {
        string sport_name
        datetime schedule_time
        string venue
        string team_a
        string team_b
        string coordinator_phone
    }

    STANDINGS {
        string chapter_name
        int points
        int rank
    }

    RULES {
        string sport_name
        text max_participation_per_chapter
        text limitation_notes
    }

    SPONSOR {
        string name
        string category "Apparel, Beverage, etc"
    }
```

## 2. Sequence Diagrams (Critical Features)

### 2.1. Master Routing Flow (Agentic Decision Making)

This flow illustrates how the system decides between using Internal Knowledge, Web Search, or Database Querying.

```mermaid
sequenceDiagram
    actor User
    participant API
    participant Graph as AgentGraph
    participant LLM as Classifier (LLM)
    participant Redis as RedisCache
    participant DB as Database
    participant Web as WebSearch
    
    User->>API: Information Query
    API->>Graph: Invoke Agent
    Graph->>Redis: Fetch Conversation History
    Redis-->>Graph: History Context
    Graph->>LLM: Classify Query (History + Current)
    
    alt IN_DOMAIN_WITHIN_PREVIOUS_CONVERSATION
        LLM-->>Graph: Chat Context
        Graph->>LLM: Answer from History
        LLM-->>Graph: Response
    else IN_DOMAIN_DB_QUERY
        LLM-->>Graph: DB Query
        Graph->>DB: (Proceed to Text-to-SQL Flow)
    else IN_DOMAIN_WEB_SEARCH
        LLM-->>Graph: Web Search
        Graph->>Web: (Proceed to Web Search Flow)
    else OUT_OF_DOMAIN
        LLM-->>Graph: General
        Graph->>LLM: General Chat Response
    end
    
    Graph-->>API: Final Answer
    API-->>User: Response
```

### 2.2. Text-to-SQL Critical Flow (DB Query)

The core logic for converting natural language to safe SQL execution.

```mermaid
sequenceDiagram
    participant Agent as Agent Node
    participant Tool as SQLToolkit
    participant LLM as Generator (LLM)
    participant Val as Validator (LLM)
    participant DB as MySQL Database
    
    Note over Agent: Validated "IN_DOMAIN_DB_QUERY"
    
    Agent->>Tool: List Tables
    Tool-->>Agent: [Table Names]
    
    Agent->>Tool: Get Schema (Relevant Tables)
    Tool-->>Agent: CREATE TABLE definitions...
    
    loop Self-Correction (Max Retries)
        Agent->>LLM: Generate SQL (Prompt + Schema)
        LLM-->>Agent: SQL Query candidate
        
        Agent->>Val: Check Query (Safety/Syntax)
        Val-->>Agent: VALID / INVALID
        
        opt IF INVALID
            Agent->>Agent: Increment Retry Count
            Note right of Agent: Loop back to Generate SQL
        end
    end
    
    alt IF VALID
        Agent->>DB: Execute SQL Query
        DB-->>Agent: Result Rows (JSON)
        Agent->>LLM: Generate Natural Response (Result + Question)
        LLM-->>Agent: Friendly Human Response
    else IF ERROR/MAX RETRIES
        Agent-->>Agent: Generate Error Response
    end
```

### 2.3. Web Search Flow (Static Info)

Optimized flow for fetching general tournament information.

```mermaid
sequenceDiagram
    participant Agent as WebSearchNode
    participant Redis as RedisCache
    participant Scraper as DirectScraper
    participant Search as WebSearchTool
    participant LLM as Summarizer
    
    Note over Agent: Validated "IN_DOMAIN_WEB_SEARCH"
    
    Agent->>Agent: Check against "Direct URLs" (Optimization)
    
    alt URL Match Found (e.g., /schedule)
        Agent->>Redis: Check Cache (URL Key)
        alt Cache Hit
            Redis-->>Agent: Cached HTML Content
        else Cache Miss
            Agent->>Scraper: Scrape Target URL
            Scraper-->>Agent: HTML Content
            Agent->>Redis: Set Cache (24h)
        end
        Agent->>LLM: Summarize Content for Answer
        LLM-->>Agent: Response
        
    else No Direct Match
        Agent->>Search: Generic Web Search (siciliangames.com)
        Search-->>Agent: Search Snippets
        Agent->>LLM: Synthesize Answer
        LLM-->>Agent: Response
    end
```

## 3. Service Dependency Diagram

Visualizes the external and internal services needed for the system to function.

```mermaid
graph TD
    Client[User Client] -->|HTTP / WhatsApp| LB[Load Balancer / Gateway]
    
    subgraph "Application Core"
        API[FastAPI Service]
        Worker[Celery/RQ Worker]
    end
    
    subgraph "Data Persistence"
        Redis[(Redis Cache & Queue)]
        MySQL[(MySQL Database)]
    end
    
    subgraph "External Integration"
        Twilio[Twilio API]
        OpenAI[OpenAI / LLM Provider]
        TargetWeb[siciliangames.com]
    end
    
    LB --> API
    API -->|Enqueue Task| Redis
    Redis -->|Consume Task| Worker
    
    API -->|Read/Write| Redis
    API -->|Query| MySQL
    Worker -->|Query| MySQL
    
    API -->|Interact| OpenAI
    Worker -->|Interact| OpenAI
    
    Client -.->|WhatsApp Msg| Twilio
    Twilio -->|Webhook| API
    Worker -->|Async Reply| Twilio
    
    API -->|Scrape| TargetWeb
```

## 4. Agentic Flow Diagram (Detailed)

Detailed internal logic of the LangGraph agent.

```mermaid
flowchart TD
    Start([Start]) --> FetchHistory[Fetch Conversation History]
    FetchHistory --> Classify{Classify Query}
    
    Classify -- Previous Context --> AnswerContext[Node: Answer from Prev Convo]
    Classify -- General/Greeting --> AnswerGeneral[Node: Answer General]
    Classify -- Web Search --> WebSearch[Node: Web Search]
    Classify -- DB Query --> ListTables[Node: List Tables]
    
    %% Web Search Sub-flow
    WebSearch --> CheckDirectURL{Direct URL?}
    CheckDirectURL -- Yes --> CheckCache{In Cache?}
    CheckCache -- Yes --> GetCache[Get Content]
    CheckCache -- No --> Scrape[Scrape & Cache]
    Scrape --> GetCache
    GetCache --> Summarize[LLM Summarize]
    CheckDirectURL -- No --> GenericSearch[Generic Web Search]
    GenericSearch --> Summarize
    Summarize --> End([End])
    
    %% DB Query Sub-flow
    ListTables --> CallSchema[Node: Call Get Schema]
    CallSchema --> GetSchema[Tool: Get Schema]
    GetSchema --> InitRetry[Init Retry Count]
    InitRetry --> GenQuery[Node: Generate SQL]
    
    GenQuery --> CheckQuery{Node: Check Query}
    
    CheckQuery -- INVALID (Retry < Max) --> GenQuery
    CheckQuery -- INVALID (Max Retries) --> GenError[Generate Error Response]
    CheckQuery -- VALID --> RunQuery[Node: Run Custom Query]
    
    RunQuery --> GenResponse[Node: Generate Natural Response]
    GenResponse --> End
    
    AnswerContext --> End
    AnswerGeneral --> End
    GenError --> End
```

## 5. Module Feature Diagram

Breakdown of features across Frontend and Backend modules.

```mermaid
block-beta
    columns 2
  
    block:Backend
        columns 1
        title("Backend (Python/FastAPI)")
        
        block:APILayer
            title("API Layer")
            endpoint_REST["/query (REST)"]
            endpoint_Hook["/webhook (WhatsApp)"]
        end
        
        block:AgentCore
            title("Agent Core")
            Router["Master Router"]
            Graph["LangGraph Engine"]
            Memory["Conversation Manager"]
        end
        
        block:Tooling
            title("Tools & Skills")
            Tool_SQL["SQL Toolkit"]
            Tool_Scrape["Web Scraper"]
            Tool_Search["Search Engine"]
        end
        
        block:Infra
            title("Infrastructure")
            DB_Mgr["Database Manager"]
            Cache_Mgr["Redis Queue Manager"]
        end
    end

    block:Frontend
        columns 1
        title("Primary Interface")
        
        block:WhatsApp
            title("WhatsApp (Via Twilio)")
            Msg_In["Incoming Message Handler"]
            Msg_Out["Async Response Handler"]
        end
        
        block:AdminUI
            title("Dev/Admin UI (Streamlit)")
            Chat_Debug["Chat Debugger"]
            Log_View["Log Viewer"]
        end
    end
    
    Backend --> Frontend
```
