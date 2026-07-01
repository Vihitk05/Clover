# Clover

Clover is an AI-powered job search and application assistant built to help a candidate move from resume upload to focused, trackable job applications. The project combines a FastAPI backend, a Next.js frontend, a job ingestion pipeline, resume parsing, semantic matching, adaptive scoring, document generation, and application tracking into one end-to-end workflow.

At its core, Clover turns an uploaded CV into a structured candidate profile, compares that profile against ingested job listings, ranks opportunities by fit, explains why each job is recommended, and helps generate application-ready materials for the strongest matches. The goal is not only to show jobs, but to make the job search more deliberate: what fits, why it fits, what skills are missing, what documents should be prepared, and what actions need to happen next.

## What Has Been Built

The application currently supports authenticated user accounts, onboarding preferences, resume uploads, personalized job matching, detailed match pages, generated application outputs, downloadable resume and cover letter assets, user feedback signals, and an application tracker. It also includes scraper services for collecting jobs from multiple sources and persisting normalized job data for matching.

The product experience starts with sign up or login. A user can provide onboarding preferences such as target roles, locations, salary expectations, work types, career goals, and skill confidence. The user then uploads a CV, and Clover extracts profile information such as name, contact details, skills, job titles, experience, education, seniority level, and career preferences. That parsed profile becomes the basis for embedding, matching, ranking, and later document generation.

Once a profile exists, Clover can match it against stored job listings. The results page shows recommended jobs with fit scores, match labels, confidence, matched skills, missing skills, and eligibility for generation. A user can filter for jobs that are strong enough for generated outputs, refresh matches, open a detailed job view, and record interaction signals as they browse.

For a selected match, Clover provides a job detail page with a personalized fit explanation, score breakdown, matched and missing skills, source information, and an external job link when available. If the match is eligible, the user can generate optimized application outputs. Generated outputs include a gap report, ATS-oriented CV rewrite, ATS score before and after optimization, keyword justifications, CV changes, a tailored cover letter, and downloadable document assets.

Clover also includes an application tracking flow. When generated documents are created, the user can save or track the application, update status, add deadlines, define next actions, and write notes. The tracker produces deterministic urgency and next-action summaries based on application status and deadlines, helping the user prioritize overdue, due-soon, active, and closed applications.

## Frontend Experience

The frontend is a Next.js application organized around the main job-search workflow:

- The home page handles authentication, session restoration, onboarding, and CV upload.
- The results page displays personalized job recommendations and lets the user refresh or filter matches.
- The job detail page explains an individual match and allows generation or regeneration of application materials.
- The profile page shows the active resume version, parsed profile details, editable profile fields, resume download, resume preview, and sign out.
- The applications page lists tracked applications with status, urgency, deadline context, and tracker summaries.
- The application detail page lets the user inspect one tracked application, update its status, deadline, next action, and notes, and download generated resume or cover letter assets.

The UI uses reusable components for layout, authentication, onboarding, CV upload, job cards, skill badges, score rings, ATS score visualization, gap analysis, and cover letter display. The client communicates with the backend through a typed API layer, stores access and refresh tokens in browser storage, automatically refreshes expired access tokens, and supports authenticated downloads for resumes and generated documents.

## Backend API

The backend is a FastAPI service that exposes the application workflow through REST endpoints. It supports health checks, local email/password authentication, OAuth-style login payloads, JWT access tokens, refresh tokens, logout, current-user lookup, onboarding create/update, profile retrieval and updates, active resume download, CV upload, match retrieval, match detail, signal recording, application creation, application listing, application updates, application detail, generated output creation, generated asset download, scraper triggering, scraper task status, and latest scraper run lookup.

Authentication is built around hashed passwords, short-lived access tokens, refresh tokens, and persisted refresh sessions. User-specific routes validate ownership so profiles, resumes, matches, generated outputs, and applications are scoped to the authenticated user.

The API stores and returns structured objects for profiles, resumes, matches, generated outputs, applications, onboarding preferences, signals, and scraper runs. Match responses include both raw and personalized fit scores, score breakdowns, labels, confidence, matched skills, missing skills, eligibility for generation, and explanations designed to be understandable to the user.

## Resume Parsing And Profile Building

Clover includes a resume parser that extracts text from PDF and DOCX files. It uses local JSON databases of known skills and job titles, then applies parsing logic to identify contact details, education, skills, job titles, experience history, years of experience, seniority, and other profile fields. Uploaded resumes are versioned, stored on disk, associated with a user profile, and marked as active so the product can support newer resume versions over time.

When a resume is uploaded, Clover creates or updates the user's profile, stores the parsed resume data, embeds the profile for later search, clears stale match data tied to older profile state, and returns the profile and resume metadata needed by the frontend.

## Matching Engine

The matching engine combines semantic similarity with rule-based, explainable scoring. It can use Gemini embeddings and ChromaDB-backed job embeddings when available, while retaining deterministic fallbacks for local development. A profile embedding is compared against job embeddings, then each candidate job is rescored using multiple dimensions:

- Semantic similarity between profile and job description.
- Skill overlap between extracted candidate skills and job skills.
- Seniority alignment between the candidate profile and the role.
- Experience fit based on estimated years required by the job.
- Internship-aware alignment for entry-level or early-career candidates.
- Project relevance for technical roles.
- Education relevance where job descriptions imply degree requirements.
- Location fit, including remote-compatible matching.

The engine also filters out roles that are clearly too senior for the candidate. It produces a final fit score, confidence, match label, score breakdown, matched skills, missing skills, generation eligibility, and a concise explanation. This gives the product a transparent ranking layer instead of a black-box list of jobs.

## Adaptive Personalization

Clover records user signals as the user interacts with matches and generated outputs. These signals can include viewed matches, generated documents, and payload details such as skills, companies, locations, and scores. The backend uses stored signals to apply personalization when returning matches, including adaptive boosts and fit explanations. This lets the system begin adapting recommendations based on what the user engages with, not only what the resume says.

## AI Agent Pipeline

Clover includes a three-step AI generation pipeline:

1. The gap analysis agent compares the candidate profile with the target job description, identifies matched skills, missing skills, weak areas, recommended learning areas, and an overall summary.
2. The ATS optimization agent rewrites the CV into a more ATS-friendly structure, adds relevant missing keywords where appropriate, estimates ATS score improvement, and records keyword justifications and CV diffs.
3. The cover letter agent generates a concise role-tailored cover letter using the candidate profile, gap report, job description, company name, and candidate name.

The pipeline is LangGraph-first when LangGraph is installed, with a sequential fallback when it is not. Gemini is used for generation and embeddings when configured, while deterministic local fallbacks keep development flows functional without external AI calls.

## Generated Documents

Generated application outputs are persisted with the match, user, profile, job, and resume version. Clover stores the gap report, rewritten CV text, cover letter text, ATS scores, fit explanation, keywords added, keyword justifications, CV diff, and paths to generated document assets. The backend exposes authenticated downloads for optimized resumes and cover letters so the frontend can retrieve them directly from the application detail or job detail pages.

## Job Ingestion And Scraping

Clover includes a scraper and ingestion layer for job listings. The project has spiders and services for sources such as jobs.ie, IrishJobs, and LinkedIn, plus API endpoints to trigger individual providers or all providers. Scraper runs are tracked with counts for pages scraped, jobs found, jobs inserted, duplicates skipped, errors, timestamps, and status.

The ingestion pipeline normalizes job payloads from HTML, JSON, and scraper output. It handles multiple field aliases for title, company, location, description, salary, posting date, employment type, work type, URL, and source. It also extracts skills, estimates seniority, parses salary information, cleans descriptions, detects work type, and prepares consistent job records for storage.

Job records are stored with source hashes to avoid duplicate daily inserts. Each job includes title, company, location, salary range, seniority, sector, raw description, extracted skills, source, URL, posting date, scrape timestamp, and active status. These jobs become the searchable corpus used by the matching engine.

## Data Model

The backend data model currently includes:
- Users, password hashes, OAuth identity fields, account status, creation timestamps, and login timestamps.
- Refresh sessions with hashed refresh tokens, expiry, user agent, IP address, and revocation state.
- User profiles with parsed resume data, skills, target role, target location, salary expectations, seniority, education, and resume version.
- Resume documents with versioning, original filename, storage path, MIME type, file size, parsed data, upload timestamp, and active state.
- Onboarding preferences with target roles, locations, salary range, work types, career goals, skill confidence, and completion state.
- Jobs with normalized listing fields, source metadata, extracted skills, and deduplication hashes.
- Match results with scores, labels, confidence, breakdowns, matched skills, missing skills, adaptive boosts, explanations, and generation eligibility.
- Generated outputs with gap reports, rewritten CVs, cover letters, ATS scores, document paths, keyword data, and CV diffs.
- User signals for personalization and interaction history.
- User applications with status, deadline, next action, notes, linked job, linked match, linked generated output, resume version, and tracker metadata.
- Scraper runs for operational visibility into ingestion jobs.

## Current Project Shape

Clover is now a working full-stack prototype of an adaptive job application assistant. It has a real user journey, persistent accounts, resume-aware profiles, explainable job matching, AI-assisted generation, document downloads, application tracking, scraper orchestration, and tests around important smoke paths such as API imports, auth, config, CV parsing, job ingestion, and matching.
The system is designed so that core flows still work during development even when external services are unavailable. Gemini, ChromaDB, LangGraph, and scraper integrations enhance the experience when configured, but local fallbacks keep the product usable for testing and iteration. This makes Clover both a practical job-search tool and a foundation for further improvements in recommendation quality, document generation, scraper reliability, and personalized career guidance.
