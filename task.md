# Backend Engineering - Take-Home Test
**Position:** Python Team Lead / Senior Python Developer
**Digital Health Platform**

---

## Overview

This take-home test evaluates your ability to build a production-quality FastAPI microservice that integrates with third-party APIs. We want to see how you approach API design, code quality, testing, and documentation.

**Important:** This is an open-ended design challenge. We want to see YOUR decisions on API structure, response formats, and error handling. You will walk us through your code and explain your design choices during the review.

**Time Expectation:** 2-4 hours (no strict deadline)
**Use of GenAI:** Strongly encouraged! We use Claude Code, and other AI tools daily.

---

## The Challenge: IP Geolocation Service

Build a FastAPI microservice that provides IP address geolocation information by integrating with a third-party IP geolocation API.

### Functional Requirements:

Your service must provide functionality to:

1. **Look up geolocation for a specific IP address**
    - Accept an IP address as input
    - Return geolocation information (country, region, city, coordinates, timezone, ISP, etc.)
    - Handle IPv4 addresses at minimum
2. **Look up geolocation for the requesting client's IP address**
   - Automatically detect the client's IP address from the request
   - Return geolocation information

---

## Technical Requirements

### Must Have:

1. **OpenAPI Specification**
    - Define OpenAPI specification as the source of truth
    - Include proper descriptions, examples, and response models
    - Avoid grammatical and spelling mistakes
    - **Your API design will be evaluated based on the OpenAPI spec**

2. **FastAPI Framework**
    - Use FastAPI to build the REST API
    - Implement the functionality described in the OpenAPI spec (how you structure it is up to you)
    - Use Pydantic models for request/response validation

3. **Generate interactive API documentation**
    - This shouldn't take long - find something to generate this from your OpenAPI spec

4. **IP Geolocation Data Source**
    - Choose ONE of these approaches (document your choice and reasoning):
      - **Option A: Third-Party API Integration**
        - Integrate with a free IP geolocation API
        - Suggested APIs to research:
          - **ip-api.com** (no auth, 45 req/min, good data quality)
          - **ipapi.co** (free tier: 1000/day, optional API key)
          - **ipgeolocation.io** (requires API key, 30K/month free)
          - **ipstack.com** (requires API key, free tier available)
          - **ipwhois.io** (no auth, free tier)
          - Or research and find your own
        - Handle API errors gracefully (rate limits, timeouts, invalid IPs)
        - Implement proper async HTTP client usage
      - **Option B: Local Database**
        - Use a local IP geolocation database
        - Suggested databases to research:
          - **MaxMind GeoLite2** (free, regularly updated, good accuracy)
          - **IP2Location LITE** (free database download)
          - **DB-IP** (free database, monthly updates)
        - Handle database setup and querying
        - Consider how you'd update the database periodically
  
    - **Your Choice:** You decide which approach to use. Document your reasoning in DEVELOPMENT_NOTES.md:
      - Why did you choose API vs local database (or vice versa)?
      - What are the trade-offs?
      - For production, which would you recommend and why?

5. **Error Handling**
   - Handle invalid IP addresses appropriately
   - Handle cases where IP information is not found
   - Handle third-party API failures and rate-limiting
   - Use proper HTTP status codes
   - Design a consistent error response format

6. **Testing**
   - Write tests using `pytest`
   - Include unit tests for core logic
   - Include integration tests (mock external API)
   - Aim for meaningful test coverage

7. **Code Quality**
   - Use type hints throughout
   - Use `ruff` for linting/formatting
   - Use `mypy` for static type checking
   - Follow Python best practices

8. **Documentation**
   - README.md with setup instructions
   - How to run the service
   - How to run tests
   - How to access API documentation
   - **Explain your API design decisions**

9. **Development Reflection (REQUIRED)**
   - Create `DEVELOPMENT_NOTES.md` documenting:
     - **Implementation walkthrough:** How did you approach building this? What did you build first?
     - **Total time spent:** Approximate hours (we just want a rough estimate)
     - **Challenges & solutions:** What did you struggle with? How did you solve it?
     - **GenAI usage:** How much did you use AI tools? What helped? What didn't?
     - **API Design Decisions:** Why did you structure your API this way?
     - **Third-party API/Database selection:** Why did you choose this approach?
     - **Production Readiness:** List 5-10 things you would implement next to make this production-ready (we'll discuss these, not implement them)

---

## What We're Evaluating

### Technical Skills:
- **API Design:** How well did you design your API structure, endpoints, and data models?
- **FastAPI expertise:** Proper use of FastAPI features (dependency injection, path parameters, async)
- **Pydantic:** Well-defined models, proper validation
- **A: Third-party integration:** Robust external API handling, error management
- **B: Database integration:** Robust database handling, error management
- **Testing:** Meaningful tests, good coverage, proper mocking
- **Code quality:** Clean code, type hints, proper structure, follows best practices

### Problem-Solving & Decision Making:
- **Error handling:** How you handle edge cases and failures
- **Design decisions:** Trade-offs and reasoning behind choices (documented in DEVELOPMENT_NOTES.md)
- **Third-party API/Database selection:** Why you chose this approach

### Documentation & Communication:
- **README clarity:** Can someone else set up and run your project?
- **API design explanation:** Can you articulate why you made specific design choices?
- **OpenAPI docs:** Well-documented API with examples
- **Development reflection:** Thoughtful analysis of your process
- **Production readiness thinking:** What would you implement next?
- **Code walkthrough readiness:** Be prepared to explain your code decisions

---

## Submission Guidelines

### What and how to submit:

**GitHub Repository**
   - Create a GitHub repository with your solution
   - Share the repository with the following GitHub users:
      - `whisller`
      - `raymondbutcher`
      - `vitalii-meleshko-livanova`
   - Ensure commit history is preserved (we want to see your development progression)

---

## Code Review Process

**Important:** After submission, you will:

1. **Walk us through your code** - Be prepared to explain your implementation
2. **Justify your API design** - Why did you structure endpoints and responses this way?
3. **Explain your error handling** - How did you decide which errors to handle and how?
4. **Discuss trade-offs** - What alternatives did you consider?
5. **Answer technical questions** - We'll probe your understanding of the implementation

This is not just about working code - it's about understanding your thought process and decision-making.

---

## Developer Guidance (Standards)

While we expect you to know industry best practices, here's what we value:

### API Design Principles:
- **RESTful principles:** Use proper HTTP methods and status codes
- **Consistency:** Maintain consistent naming conventions and response structures
- **Versioning:** Consider how you would version your API
- **Documentation:** Your OpenAPI spec should be self-explanatory
- **Error responses:** Design a consistent error format across all endpoints

### Code Organization:
- Separate concerns (routers, services, models)
- Configuration management
- Reusable components
- Logical file structure

### Testing Principles:
- Test the happy path AND edge cases
- Mock external API calls
- Use pytest fixtures for common setup
- Clear test names that explain what's being tested

### What We're Looking For:
- **Pragmatic solutions** over over-engineering
- **Clear reasoning** for design choices
- **Production mindset** (error handling, logging, configuration)
- **Ability to articulate decisions** during code review
- **Tidy work** (simple and easy-to-read code, no mess)

---

## Frequently Asked Questions

**Q: How much time should I spend?**
A: 2-4 hours is typical. Don't spend more than 6 hours. We value your time.

**Q: Can I use AI tools?**
A: Yes! We encourage it. Just document your usage in DEVELOPMENT_NOTES.md.

**Q: Should I implement production features like monitoring, CI/CD, caching?**
A: No. Focus on core functionality. Document what you WOULD implement next in DEVELOPMENT_NOTES.md. We'll discuss these during code review.

**Q: What if I get stuck?**
A: Document the problem in DEVELOPMENT_NOTES.md. Explain what you tried. This is valuable insight. If you get totally stuck, find a work-around, document it, and continue with the rest of the exercise.

**Q: Can I use libraries beyond FastAPI?**
A: Yes! Use whatever you need. Document your choices.

**Q: How important is the OpenAPI specification?**
A: Very important! This is a core part of how we develop. Well-defined Pydantic models and good API docs are critical.

**Q: Will you run my code?**
A: Yes, but more importantly, you'll walk us through it. Be prepared to explain every design decision.

**Q: What if I'm not sure about an API design choice?**
A: Make a decision, document your reasoning in DEVELOPMENT_NOTES.md, and be ready to discuss alternatives during the review.

---

## Questions?

If you have questions about this assignment, please contact your recruiting contact. We're happy to clarify requirements before you start.

---

## Final Note

We're excited to see your solution! This test is designed to be realistic - similar to tasks you'd work on at COMPANY.

**Remember:**
- This is YOUR design. We want to see your decisions, not a copy of a tutorial.
- Be prepared to walk through your code and explain your choices.
- Document your reasoning so we understand your thought process.
- There's no single "correct" answer - we're evaluating your approach and justification.

**Good luck, and have fun building!** 🚀
