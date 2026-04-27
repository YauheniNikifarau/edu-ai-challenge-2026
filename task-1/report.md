# Report — AI Challenge 2.0 (Task 1: Leaderboard Clone)

## Overview
In this task, I built a replica of the internal company leaderboard using AI-assisted development (“vibe coding”). The goal was to reproduce the UI and functionality while avoiding the use of any real corporate data.

## Tools Used
- Abacus AI (ChatLLM / Agent)
- Claude (AI assistant)
- Browser DevTools (for inspecting and modifying the original UI safely)

## Approach

### 1. Role-Based Prompting
I used a role-based workflow to structure the development process:

- **Business Analyst role**  
  First, I prompted the AI to act as a business analyst and generate structured artifacts based on the observed leaderboard:
    - feature breakdown
    - UI components description
    - filtering and sorting logic
    - data schema

- **Senior Frontend Engineer role**  
  Next, I asked the AI to implement the application strictly based on the previously defined artifacts.  
  This helped ensure consistency and reduced hallucinations.

- **Frontend Tech Lead role (Code Review)**  
  Finally, I prompted the AI to review the generated code as a tech lead:
    - checked correctness of UI behavior
    - validated sorting/filtering logic
    - improved structure and readability

This multi-step prompting approach improved both quality and reliability of the final result.

## Data Handling & Compliance

To comply with responsible AI usage policies:

- I **did not send any real corporate data to AI tools**
- Before interacting with AI, I:
    - opened the original leaderboard in the browser
    - used **DevTools to edit the HTML directly**
    - replaced all sensitive data (names, departments, titles, etc.) with fake placeholders

- Only **sanitized (fake) data** was used in prompts and in the final application

This ensured zero leakage of real internal information.

## Result

The final application:
- replicates the original leaderboard UI and behavior
- includes all required functionality (sorting, filtering, layout)
- uses only synthetic data
- is deployed via GitHub Pages

## Conclusion

Using a structured, role-based prompting approach with multiple AI tools allowed me to efficiently build a high-quality replica without writing code manually. Separating analysis, implementation, and review stages proved especially effective for controlling output quality and maintaining alignment with requirements.