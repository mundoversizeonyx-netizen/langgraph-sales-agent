---
description: Multi-agent workflow for enterprise-grade agentic code development
---

# Multi-Agent Development Workflow

This workflow orchestrates multiple specialized agents to deliver production-ready agentic code with proper architecture, implementation, testing, and documentation.

## Agent Roles

### 1. Architecture Agent 🏗️
**Responsibility**: System design, architecture decisions, component boundaries
**Outputs**: Architecture diagrams, design documents, API contracts

### 2. Implementation Agent 💻
**Responsibility**: Writing clean, maintainable, production-ready code
**Outputs**: Source code, configuration files, infrastructure code

### 3. Code Review Agent 🔍
**Responsibility**: Quality assurance, best practices, security review
**Outputs**: Review comments, refactoring suggestions, approval/rejection

### 4. Testing Agent 🧪
**Responsibility**: Test coverage, edge cases, integration testing
**Outputs**: Unit tests, integration tests, test reports

### 5. Documentation Agent 📚
**Responsibility**: User guides, API docs, architecture documentation
**Outputs**: README files, API documentation, runbooks

## Workflow Steps

### Phase 1: Requirements & Architecture (Architecture Agent)
1. Analyze the user's requirements and objectives
2. Create a high-level architecture document
3. Define component boundaries and interfaces
4. Identify potential risks and mitigation strategies
5. Create a requirements traceability matrix
6. **Output**: `docs/architecture/ARCHITECTURE.md`

### Phase 2: Design Review (Code Review Agent)
7. Review the proposed architecture
8. Validate design patterns and best practices
9. Check for scalability and maintainability concerns
10. Suggest improvements or approve design
11. **Output**: `docs/architecture/DESIGN_REVIEW.md`

### Phase 3: Implementation Planning (Architecture Agent)
12. Break down the architecture into implementable tasks
13. Define implementation order and dependencies
14. Create API contracts and interfaces
15. **Output**: `docs/implementation/IMPLEMENTATION_PLAN.md`

### Phase 4: Code Implementation (Implementation Agent)
16. Implement core components following the architecture
17. Follow coding standards and best practices
18. Add inline documentation and type hints
19. Implement error handling and logging
20. **Output**: Source code files

### Phase 5: Code Review (Code Review Agent)
21. Review implementation for correctness
22. Check adherence to architecture and patterns
23. Validate error handling and edge cases
24. Review security implications
25. Check code style and maintainability
26. **Output**: `docs/reviews/CODE_REVIEW_[timestamp].md`

### Phase 6: Test Development (Testing Agent)
27. Write unit tests for all components
28. Create integration tests for workflows
29. Add edge case and error condition tests
30. Validate test coverage (aim for >80%)
31. **Output**: Test files in `tests/` directory

### Phase 7: Test Review (Code Review Agent)
32. Review test quality and coverage
33. Validate test scenarios and edge cases
34. Ensure tests are maintainable
35. **Output**: Test approval or improvement suggestions

### Phase 8: Documentation (Documentation Agent)
36. Create comprehensive README
37. Document API endpoints and usage
38. Write deployment and configuration guides
39. Create troubleshooting runbook
40. **Output**: Documentation in `docs/` directory

### Phase 9: Final Review (All Agents)
41. Architecture Agent: Verify implementation matches design
42. Code Review Agent: Final quality check
43. Testing Agent: Validate all tests pass
44. Documentation Agent: Ensure docs are complete
45. **Output**: `docs/RELEASE_NOTES.md`

## Usage

To start a multi-agent development session:

```bash
# User initiates with a feature request
"I need to build [feature description]"

# Agent responds with:
"Starting multi-agent workflow for [feature]. I'll coordinate between Architecture, Implementation, Code Review, Testing, and Documentation agents."
```

## Agent Communication Protocol

Each agent creates artifacts in specific directories:

```
project/
├── .agent/
│   └── workflows/
├── docs/
│   ├── architecture/      # Architecture Agent outputs
│   ├── implementation/    # Implementation plans
│   ├── reviews/          # Code Review Agent outputs
│   └── api/              # Documentation Agent outputs
├── src/                  # Implementation Agent outputs
└── tests/                # Testing Agent outputs
```

## Quality Gates

Each phase has quality gates that must pass before proceeding:

- **Architecture Review**: Design must be approved by Code Review Agent
- **Code Review**: Implementation must pass review before testing
- **Test Coverage**: Must achieve minimum coverage threshold
- **Documentation**: Must be complete and accurate

## Turbo Mode

For rapid iteration on approved patterns:

```markdown
// turbo-all
```

Add this annotation to auto-approve safe, repetitive tasks.

## Example Session

```
USER: "Build an AI sales agent that handles customer inquiries"

ARCHITECTURE AGENT:
- Analyzes requirements
- Designs multi-agent architecture
- Creates component diagram
- Outputs: docs/architecture/ARCHITECTURE.md

CODE REVIEW AGENT:
- Reviews architecture
- Suggests improvements
- Approves design
- Outputs: docs/architecture/DESIGN_REVIEW.md

IMPLEMENTATION AGENT:
- Implements core agents
- Adds tool integrations
- Implements state management
- Outputs: src/agents/, src/tools/, src/state/

CODE REVIEW AGENT:
- Reviews implementation
- Checks patterns and practices
- Validates error handling
- Outputs: docs/reviews/CODE_REVIEW_001.md

TESTING AGENT:
- Writes unit tests
- Creates integration tests
- Validates coverage
- Outputs: tests/unit/, tests/integration/

DOCUMENTATION AGENT:
- Creates README
- Documents APIs
- Writes deployment guide
- Outputs: README.md, docs/api/, docs/deployment/
```

## Benefits

✅ **Structured Process**: Clear phases and handoffs
✅ **Quality Assurance**: Multiple review checkpoints
✅ **Comprehensive Coverage**: Architecture, code, tests, docs
✅ **Traceable Decisions**: All decisions documented
✅ **Production Ready**: Enterprise-grade output
