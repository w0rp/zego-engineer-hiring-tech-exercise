# python-developer-test

# Zego

## About Us

At Zego, we understand that traditional motor insurance holds good drivers back.
It's too complicated, too expensive, and it doesn't reflect how well you actually drive.
Since 2016, we have been on a mission to change that by offering the lowest priced insurance for good drivers.

From van drivers and gig economy workers to everyday car drivers, our customers are the driving force behind everything we do. We've sold tens of millions of policies and raised over $200 million in funding. And we’re only just getting started.

## Our Values

Zego is thoroughly committed to our values, which are the essence of our culture. Our values defined everything we do and how we do it.
They are the foundation of our company and the guiding principles for our employees. Our values are:

<table>
    <tr><td><img src="../doc/assets/blaze_a_trail.png?raw=true" alt="Blaze a trail" width=50></td><td><b>Blaze a trail</b></td><td>Emphasize curiosity and creativity to disrupt the industry through experimentation and evolution.</td></tr>
    <tr><td><img src="../doc/assets/drive_to_win.png?raw=true" alt="Drive to win" width=50></td><td><b>Drive to win</b></td><td>Strive for excellence by working smart, maintaining well-being, and fostering a safe, productive environment.</td></tr>
    <tr><td><img src="../doc/assets/take_the_wheel.png?raw=true" alt="Take the wheel" width=50></td><td><b>Take the wheel</b></td><td>Encourage ownership and trust, empowering individuals to fulfil commitments and prioritize customers.</td></tr>
    <tr><td><img src="../doc/assets/zego_before_ego.png?raw=true" alt="Zego before ego" width=50></td><td><b>Zego before ego</b></td><td>Promote unity by working as one team, celebrating diversity, and appreciating each individual's uniqueness.</td></tr>
</table>

## The Engineering Team

Zego puts technology first in its mission to define the future of the insurance industry.
By focusing on our customers' needs we're building the flexible and sustainable insurance products
and services that they deserve. And we do that by empowering a diverse, resourceful, and creative
team of engineers that thrive on challenge and innovation.

### How We Work

- **Collaboration & Knowledge Sharing** - Engineers at Zego work closely with cross-functional teams to gather requirements,
  deliver well-structured solutions, and contribute to code reviews to ensure high-quality output.
- **Problem Solving & Innovation** - We encourage analytical thinking and a proactive approach to tackling complex
  problems. Engineers are expected to contribute to discussions around optimization, scalability, and performance.
- **Continuous Learning & Growth** - At Zego, we provide engineers with abundant opportunities to learn, experiment and
  advance. We positively encourage the use of AI in our solutions as well as harnessing AI-powered tools to automate
  workflows, boost productivity and accelerate innovation. You'll have our full support to refine your skills, stay
  ahead of best practices and explore the latest technologies that drive our products and services forward.
- **Ownership & Accountability** - Our team members take ownership of their work, ensuring that solutions are reliable,
  scalable, and aligned with business needs. We trust our engineers to take initiative and drive meaningful progress.

## Who should be taking this test?

This test has been created for all levels of developer, Junior through to Staff Engineer and everyone in between.
Ideally you have hands-on experience developing Python solutions using Object Oriented Programming methodologies in a commercial setting. You have good problem-solving abilities, a passion for writing clean and generally produce efficient, maintainable scaleable code.

## The test 🧪

Create a Python app that can be run from the command line that will accept a base URL to crawl the site.
For each page it finds, the script will print the URL of the page and all the URLs it finds on that page.
The crawler will only process that single domain and not crawl URLs pointing to other domains or subdomains.
Please employ patterns that will allow your crawler to run as quickly as possible, making full use any
patterns that might boost the speed of the task, whilst not sacrificing accuracy and compute resources.
Do not use tools like Scrapy or Playwright. You may use libraries for other purposes such as making HTTP requests, parsing HTML and other similar tasks.

## The objective

This exercise is intended to allow you to demonstrate how you design software and write good quality code.
We will look at how you have structured your code and how you test it. We want to understand how you have gone about
solving this problem, what tools you used to become familiar with the subject matter and what tools you used to
produce the code and verify your work. Please include detailed information about your IDE, the use of any
interactive AI (such as Copilot) as well as any other AI tools that form part of your workflow.

You might also consider how you would extend your code to handle more complex scenarios, such a crawling
multiple domains at once, thinking about how a command line interface might not be best suited for this purpose
and what alternatives might be more suitable. Also, feel free to set the repo up as you would a production project.

Extend this README to include a detailed discussion about your design decisions, the options you considered and
the trade-offs you made during the development process, and aspects you might have addressed or refined if not constrained by time.

## Solution

This project was built with some instructions and Codex, with GPT 5.5 on xhigh
mode. The project was bootstrapped with a Dense Analysis Python skeleton for
creating new projects. The project was built initially with all Python first
party library functions, then enhanced with httpx for speed.

This project implements a command-line crawler that accepts one HTTP or HTTPS
base URL, fetches pages from that exact hostname, and prints each crawled page
with the hyperlinks found on it as soon as that page has been fetched and
parsed.

Run it with:

```sh
uv run python -m zego_tech_exercise https://example.com
```

Optional controls are available for resource usage:

```sh
uv run python -m zego_tech_exercise https://example.com \
  --concurrency 10 \
  --timeout 10 \
  --max-pages 100
```

The output is deliberately plain text so it can be read by humans or piped to
other tools. Because pages are fetched concurrently, pages are printed in the
order they finish rather than sorted URL order:

```text
https://example.com/
  https://example.com/about
  https://external.example/
https://example.com/about
  https://example.com/
```

## Design decisions

The crawler is split into a small reusable crawling module and a thin CLI
entrypoint. The module exposes `CrawlConfig`, `PageLinks`, `crawl_site`,
`extract_links`, and URL helpers so the behaviour can be tested without making
real network requests. The CLI is responsible only for argument parsing,
warning output, and rendering each parsed page yielded by the crawler.

HTTP requests are made through a shared `httpx.Client` so connections can be
kept alive and reused across page fetches. `html.parser.HTMLParser` extracts
`a[href]` links, and `concurrent.futures.ThreadPoolExecutor` provides bounded
concurrency. This keeps the implementation simple while avoiding the repeated
TCP/TLS setup cost that dominates many same-domain crawls.

URLs are normalised before they are stored or compared: fragments are removed,
relative links are resolved, schemes and hostnames are normalised to lower case,
empty paths become `/`, and default HTTP/HTTPS ports are stripped. Only `http`
and `https` links are retained. The crawler prints all links found on a crawled
page, including external domains, but it only queues links whose hostname
exactly matches the base URL hostname. That means subdomains such as
`www.example.com` or `blog.example.com` are reported but not crawled when the
base hostname is `example.com`.

Concurrency is intentionally bounded with `--concurrency` so the crawler can be
fast without creating unbounded network load. The same value is used for the
HTTP connection pool limits, which keeps request concurrency and pooled
connections aligned. `--timeout` prevents individual requests from hanging
indefinitely, and `--max-pages` gives a simple safety limit for exploratory
runs. Fetch errors are reported as warnings and do not stop the rest of the
crawl.

## Options considered

Using Scrapy or Playwright would provide more features, but the exercise
explicitly excludes those tools and they would be heavy for the required
behaviour. A fully asynchronous implementation using `asyncio` was also
considered, but the standard library does not provide a high-level async HTTP
client. Threads are a simpler fit here because the work is I/O-bound and the
required concurrency is modest.

Adding a third-party HTTP library increases the dependency surface, but profiling
showed repeated connection setup dominating same-host crawls. `httpx` is used
for synchronous connection pooling while keeping the crawler's concurrency model
simple. Beautiful Soup would improve malformed HTML handling, but standard
library parsing is accurate enough for conventional anchor links and avoids an
additional parser dependency.

The crawler currently extracts only `a[href]` links. It intentionally does not
extract images, scripts, stylesheets, `area[href]`, JavaScript-discovered
routes, or inline text URLs. That keeps the definition of a page link clear and
matches the command-line output requested by the exercise.

## Verification

The project was verified with:

```sh
uv run pytest
uv run pyright
uv run ruff check
```

The tests cover URL normalisation, ignored schemes, exact-hostname filtering,
anchor extraction, duplicate suppression, same-domain crawling, external and
subdomain reporting without crawling, fetch-error handling, `--max-pages`, and
basic CLI validation.

## Development workflow and tooling

Development was performed in a command-line environment using `uv` for project
execution, `pytest` for tests, `pyright` for strict type checking, and `ruff`
for linting. Repository exploration used shell tools including `rg`, `sed`, and
Git status checks.

Interactive AI assistance was used via Codex to inspect the repository, plan
the implementation, edit the code, update tests and documentation, and run the
verification commands. No generated code was accepted without running the local
test, lint, and type-checking commands above.

## Future refinements

Given more time, the crawler could be extended with robots.txt support,
sitemap discovery, response-size limits, retry and backoff policy, structured
JSON output, persistent crawl state, per-host rate limiting, configurable URL
normalisation rules, and richer observability. For larger crawls or multiple
domains, a long-running service with a job queue, worker pool, database-backed
state, and API-driven control plane would be more appropriate than a one-shot
CLI process.

# Instructions

1. Create a repo.
2. Tackle the test.
3. Push the code back.
4. Add us (@nktori, @danyal-zego, @bogdangoie, @cypherlou, @marliechiller and @ZEGODiogoAlves) as collaborators and tag us to review.
5. Notify your TA so they can chase the reviewers.
