# 🎯 How to Use Cursor Rules with AI Prompts

This guide explains how to effectively use the Fledge Cursor rules for Python development and documentation in your AI prompts and development workflow.

## 📁 Directory Structure

Rules are organized for Python development and documentation:

```
.cursor/rules/
├── C
│   ├── core.mdc          # Core C++ Standards + + platform requirements
│   └── plugins
│       ├── filter.mdc    # C++ filter plugin rules
│       ├── north.mdc     # C++ north plugin rules
│       └── south.mdc     # C++ south plugin rules
├── README.md             # This usage guide
├── python/               # Python-specific rules (Python 3.8.10-3.12, Ubuntu LTS 20.04+, Raspberry Pi)
│   ├── core.mdc          # Core Python standards + platform requirements
│   ├── api.mdc           # REST API + web framework dependencies
│   ├── config.mdc        # Configuration management + validation deps
│   └── quality.mdc       # Dependencies, logging, performance + requirements.txt
├── tests/                # Testing-specific rules
│   └── python/           # Python testing rules
│       ├── unit.mdc      # Unit testing rules - pytest, coverage, best practices
│       └── api.mdc       # API integration testing rules - conftest fixtures, http.client patterns
└── docs.mdc              # Documentation guidelines
```

## 📋 Available Rule Files

| Rule File | Purpose | Applies To |
|-----------|---------|------------|
| `@C/core` | Core C++ standards,| `*.h`, `*.cpp` |
| `@C/plugins/south` | C++ South Plugin| `*.h`, `*.cpp` |
| `@C/plugins/north` | C++ North Plugin| `*.h`, `*.cpp` |
| `@C/plugins/filter` | C++ Filter Plugin| `*.h`, `*.cpp` |
| `@python/core` | Core Python standards, naming, imports | `*.py`, `python/**/*` |
| `@python/api` | REST APIs, routes, middleware | API files, routes.py, web middleware |
| `@python/config` | Configuration system, data formats | Config files, configuration modules |
| `@python/quality` | Dependencies, logging, performance | Requirements files |
| `@tests/python/unit` | Unit testing with pytest | Unit test files, test configuration |
| `@tests/python/api` | API integration testing with http.client | API integration test files, conftest.py |
| `@docs` | Documentation writing | `docs/**/*`, `*.rst` |

## 🏗️ Shared Platform & Dependencies

All Python rules include consistent platform and dependency information:

### **Platform Requirements** (Built into all Python rules)
- **C++ Standard**: C++11
- **Python Versions**: 3.8.10 - 3.12 (inclusive)
- **Ubuntu**: LTS versions, 20.04 onwards (x86_64 & aarch64)
- **Raspberry Pi OS**: Bullseye and Bookworm (aarch64 & armv7l)

### **Dependencies Management** (Referenced in all Python rules)
- **[python/requirements.txt](python/requirements.txt)** - Runtime dependencies
- **[python/requirements-dev.txt](python/requirements-dev.txt)** - Development dependencies  
- **[python/requirements-test.txt](python/requirements-test.txt)** - Testing dependencies

### **Automatic Context** (No need to repeat in prompts)
When you use any `@python/*` rule, the AI automatically knows:
```bash
# Instead of writing this every time:
"Create a Python function that works on Python 3.8.10-3.12, Ubuntu LTS 20.04+, Raspberry Pi, uses requirements.txt for dependencies..."

# You can simply write:
@python/core "Create a Python function"
# The AI already knows the platform and dependency constraints!
```

## 🔄 Automatic Rule Application

Cursor automatically applies rules based on the files you're working with:

```yaml
# Example: Working on Python files automatically applies python/core rules
python/fledge/services/core/server.py → @python/core rules active

# Working on API files applies both core and API rules  
python/fledge/services/core/api/auth.py → @python/core + @python/api rules active

# Documentation files apply docs rules
docs/quick_start/installing.rst → @docs rules active
```

## 🎯 Explicit Rule References in Prompts

### Direct Rule Invocation
```
@python/core Can you help me write a function that follows Fledge Python standards?

@python/api I need to create a new REST endpoint for device management

@docs Help me write documentation for this new feature
```

### Multiple Rule References
```
@python/core @python/quality Help me refactor this code with proper error handling

@python/api @python/config Create an API endpoint for configuration management

@docs @python/api Document this REST API following both documentation and API standards

@python/core @tests/python/unit Create a service class with comprehensive unit tests

@tests/python/api @python/api Create API integration tests for new REST endpoints
```

## 💡 Context-Aware Prompts

### When Working on Python Files
```
# Cursor automatically knows to apply Python rules
"Create a new service class that handles sensor data processing"

# The AI will automatically follow:
- snake_case naming conventions
- Type hints and docstrings  
- FLCoreLogger usage
- Async/await patterns
- Error handling standards
- Python 3.8.10-3.12 compatibility
```

### When Working on Documentation
```
# In docs/ directory, rules automatically apply
"Document this new plugin API"

# The AI will automatically:
- Use reStructuredText format
- Follow Sphinx conventions
- Avoid "Fledge" in headings where possible
- Include proper cross-references
- Use correct heading hierarchy
```

## 🛠️ Specific Rule-Based Requests

### Configuration Management
```
Using @python/config rules, create a configuration category for my new plugin with:
- String, integer, and boolean parameters
- Proper validation
- Default values wrapped in quotes
- Reserved category name checking
```

### API Development
```
Following @python/api rules, create a REST endpoint that:
- Handles role-based access through middleware
- Returns camelCase JSON responses
- Includes proper error handling
- Checks for route conflicts
- Uses FLCoreLogger for logging
```

### Unit Testing
```
Using @tests/python/unit rules, create unit tests that:
- Use pytest framework
- Include proper mocking with pytest-mock
- Test both success and failure cases
- Follow the test file naming conventions
- Include code coverage setup
```

### API integration Testing
```
Using @tests/python/api rules, create API integration tests that:
- Use http.client library exclusively (no requests)
- Leverage conftest.py fixtures like reset_and_start_fledge
- Test API endpoints with proper authentication
- Use fledge_url and storage_plugin fixtures
- Follow system test organization patterns
```

### Documentation
```
Following @docs rules, create documentation that:
- Uses reStructuredText format
- Includes proper Sphinx directives
- Avoids excessive "Fledge" branding
- Has correct heading hierarchy
- Includes cross-references to related docs
```

## 🔀 Advanced Rule Usage

### API Documentation
```
Using @docs rules, create documentation for this Python API (@python/api) 
that includes proper Sphinx directives and avoids excessive Fledge branding.
```

### Complete Feature Development
```
I'm creating a new Fledge service that includes:
- Python backend (@python/core @python/api)
- Configuration management (@python/config)  
- Unit testing (@tests/python/unit)
- API integration testing (@tests/python/api)
- Complete documentation (@docs)
```

## 🔍 Rule-Aware Code Reviews

```
Review this code against @python/core and @python/quality rules:
- Check naming conventions (snake_case vs camelCase)
- Verify proper logging usage (FLCoreLogger)
- Ensure type hints are present
- Validate error handling patterns
- Check Python version compatibility

Review this test code against @tests/python/unit rules:
- Validate pytest usage and fixture patterns
- Check mocking strategies and test isolation
- Ensure proper test organization and naming
- Verify code coverage approach
```

## 🚀 Platform-Specific Development

```
# Old way (verbose, repetitive):
Using @python/core rules, help me optimize this code for:
- Raspberry Pi ARM architecture (aarch64, armv7l)
- Python 3.8.10-3.12 compatibility
- Edge device memory constraints
- Ubuntu LTS 20.04+ deployment

# New way (automatic platform context):
@python/core Optimize this code for edge device performance

# The AI automatically knows:
# - Python 3.8.10-3.12 compatibility
# - Ubuntu LTS 20.04+ (x86_64 & aarch64)
# - Raspberry Pi OS (aarch64 & armv7l)
# - Edge device memory constraints
# - Requirements.txt dependency management
```

## 🐛 Troubleshooting with Rules

```
This code isn't following @python/api middleware patterns. 
Help me fix the authentication and role validation.

This documentation doesn't follow @docs anti-branding guidelines.
Help me remove excessive "Fledge" references while maintaining clarity.
```

## 🔧 Pro Tips for Using Rules Effectively

### 1. Let Rules Work Automatically
- Just open files in the appropriate directories
- Cursor applies rules based on file patterns (globs)
- No need to explicitly mention rules for basic tasks
- Rules are automatically in context

### 2. Use Rule Names for Specific Guidance
- When you need specific standards applied
- When working across multiple technologies
- When you want to ensure compliance with particular guidelines
- When combining multiple rule sets

### 3. Combine Rules for Complex Tasks
- Use multiple @ references for cross-cutting concerns
- Leverage rule interactions (e.g., API + Config + Testing)
- Apply domain-specific and quality rules together

### 4. Rule-Based Learning
```
Explain the difference between @python/core naming conventions 
and @python/api response formatting.

How do @python/config validation rules work with @python/api endpoints?
```

### 5. Validation Against Rules
```
Does this code follow @python/quality standards for:
- Dependencies management
- Logging practices  
- Performance optimization

Does this testing code follow @tests/python/unit standards for:
- pytest usage and fixtures
- Mocking patterns
- Test coverage
- Unit testing best practices

Does this API test follow @tests/python/api standards for:
- http.client usage
- conftest.py fixture usage
- API testing patterns

Validate this documentation against @docs standards for:
- reStructuredText formatting
- Sphinx directives
- Cross-references
- Branding guidelines
```

## 📖 Rule-Specific Examples

### Python Core (@python/core)
```
Create a device manager class that:
- Uses snake_case naming
- Includes proper docstrings
- Has type hints for all methods
- Uses FLCoreLogger for logging
- Follows the server.py architectural pattern
```

### API Development (@python/api)
```
Create a REST endpoint for asset management that:
- Uses role-based middleware validation
- Returns camelCase JSON responses
- Handles route conflicts
- Includes proper error handling
- Uses async/await patterns
```

### Configuration (@python/config)
```
Design a configuration category that:
- Includes string, integer, boolean, and JSON types
- Has proper validation rules
- Uses quoted default values
- Avoids reserved category names
- Includes optional validation constraints
```

### Documentation (@docs)
```
Write API documentation that:
- Uses reStructuredText format
- Includes proper Sphinx directives
- Avoids excessive "Fledge" branding
- Has correct heading hierarchy
- Includes cross-references to related docs
```

### Unit Testing (@tests/python/unit)
```
Create comprehensive unit tests that:
- Use pytest with proper fixtures
- Mock external dependencies appropriately
- Achieve meaningful test coverage
- Follow unit testing best practices
- Test both success and failure scenarios
```

### API integration Testing (@tests/python/api)
```
Create API integration tests that:
- Use http.client library exclusively
- Leverage conftest.py fixtures for environment setup
- Test API endpoints with authentication flows
- Use reset_and_start_fledge for clean test environments
- Follow system test organization patterns
```

### Dependencies & Quality (@python/quality)
```
Manage dependencies and code quality:
- Use requirements.txt for dependency management
- Follow FLCoreLogger patterns for logging
- Optimize for edge device performance
- Ensure Python version compatibility
- Document dependency constraints
```

## 🎯 Best Practices Summary

1. **Trust Automatic Application**: Let Cursor apply rules based on file context
2. **Use @ References Explicitly**: When you need specific rule compliance
3. **Combine Rules Strategically**: For Python development with documentation
4. **Validate Against Rules**: Use rules for code review and quality checks
5. **Focus on Core Technologies**: Leverage Python and documentation rules together

The rules work best when you let them guide development naturally - they'll automatically apply standards and catch issues as you code! 