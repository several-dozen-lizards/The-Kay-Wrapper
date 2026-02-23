"""
GitHub Service for Kay Zero

Read-only access to GitHub repositories, issues, and documentation.
Supports both public repos (no auth) and private repos (with PAT).

Rate limits:
- No token: 60 requests/hour
- With token: 5000 requests/hour
"""

import os
import time
import base64
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class GitHubService:
    """
    Read-only GitHub API client for Kay.

    Usage:
        github = GitHubService()
        content = github.get_file_contents("owner/repo", "path/to/file.py")
        issues = github.search_issues("owner/repo", "memory bug")
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str = None):
        """
        Initialize GitHub service.

        Args:
            token: GitHub Personal Access Token (optional, but recommended)
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.session = requests.Session()

        # Set headers
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "KayZero-GitHub-Reader"
        })

        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"
            print("[GITHUB] Authenticated with token (5000 req/hr limit)")
        else:
            print("[GITHUB] No token - using public access (60 req/hr limit)")

        # Response cache (brief caching to avoid burning rate limits)
        self._cache: Dict[str, tuple] = {}  # url -> (response, timestamp)
        self._cache_ttl = 300  # 5 minutes

        # Rate limit tracking
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    def _get(self, endpoint: str, params: dict = None) -> Dict[str, Any]:
        """
        Make GET request to GitHub API with caching and rate limit handling.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            JSON response as dict

        Raises:
            GitHubError: On API errors
        """
        url = f"{self.BASE_URL}{endpoint}"
        cache_key = f"{url}?{params}" if params else url

        # Check cache
        if cache_key in self._cache:
            cached_response, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return cached_response

        # Check rate limit before request
        if self.rate_limit_remaining is not None and self.rate_limit_remaining <= 0:
            if self.rate_limit_reset and time.time() < self.rate_limit_reset:
                reset_time = datetime.fromtimestamp(self.rate_limit_reset)
                raise GitHubRateLimitError(
                    f"Rate limit exceeded. Resets at {reset_time.strftime('%H:%M:%S')}"
                )

        try:
            response = self.session.get(url, params=params, timeout=10)

            # Update rate limit tracking
            self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 60))
            self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

            if response.status_code == 200:
                data = response.json()
                self._cache[cache_key] = (data, time.time())
                return data

            elif response.status_code == 404:
                raise GitHubNotFoundError(f"Not found: {endpoint}")

            elif response.status_code == 401:
                raise GitHubAuthError("Invalid or expired token")

            elif response.status_code == 403:
                if "rate limit" in response.text.lower():
                    reset_time = datetime.fromtimestamp(self.rate_limit_reset)
                    raise GitHubRateLimitError(
                        f"Rate limit exceeded. Resets at {reset_time.strftime('%H:%M:%S')}"
                    )
                raise GitHubError(f"Access forbidden: {response.text}")

            else:
                raise GitHubError(f"API error {response.status_code}: {response.text}")

        except requests.RequestException as e:
            raise GitHubError(f"Network error: {e}")

    def get_file_contents(
        self,
        repo: str,
        path: str,
        branch: str = "main"
    ) -> str:
        """
        Get contents of a file from a repository.

        Args:
            repo: Repository in "owner/repo" format
            path: Path to file within repo
            branch: Branch name (default: main)

        Returns:
            File contents as string
        """
        endpoint = f"/repos/{repo}/contents/{path}"
        params = {"ref": branch}

        data = self._get(endpoint, params)

        if isinstance(data, list):
            # Path is a directory, not a file
            raise GitHubError(f"'{path}' is a directory, not a file. Use list_directory() instead.")

        if data.get("type") != "file":
            raise GitHubError(f"'{path}' is not a file (type: {data.get('type')})")

        # Decode base64 content
        content = data.get("content", "")
        encoding = data.get("encoding", "")

        if encoding == "base64":
            try:
                return base64.b64decode(content).decode("utf-8")
            except Exception as e:
                raise GitHubError(f"Failed to decode file content: {e}")
        else:
            return content

    def list_directory(
        self,
        repo: str,
        path: str = "",
        branch: str = "main"
    ) -> List[Dict[str, str]]:
        """
        List files and directories in a repository path.

        Args:
            repo: Repository in "owner/repo" format
            path: Path within repo (empty for root)
            branch: Branch name (default: main)

        Returns:
            List of dicts with 'name', 'type', 'path', 'size' keys
        """
        endpoint = f"/repos/{repo}/contents/{path}" if path else f"/repos/{repo}/contents"
        params = {"ref": branch}

        data = self._get(endpoint, params)

        if not isinstance(data, list):
            raise GitHubError(f"'{path}' is a file, not a directory. Use get_file_contents() instead.")

        return [
            {
                "name": item["name"],
                "type": item["type"],  # "file" or "dir"
                "path": item["path"],
                "size": item.get("size", 0)
            }
            for item in data
        ]

    def get_readme(self, repo: str, branch: str = "main") -> str:
        """
        Get README file from a repository.

        Args:
            repo: Repository in "owner/repo" format
            branch: Branch name (default: main)

        Returns:
            README contents as string
        """
        endpoint = f"/repos/{repo}/readme"
        params = {"ref": branch}

        data = self._get(endpoint, params)

        content = data.get("content", "")
        encoding = data.get("encoding", "")

        if encoding == "base64":
            try:
                return base64.b64decode(content).decode("utf-8")
            except Exception as e:
                raise GitHubError(f"Failed to decode README: {e}")
        else:
            return content

    def search_issues(
        self,
        repo: str,
        query: str = "",
        state: str = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search issues and PRs in a repository.

        Args:
            repo: Repository in "owner/repo" format
            query: Search query (optional)
            state: "open", "closed", or "all"
            limit: Maximum results to return

        Returns:
            List of issue dicts with title, number, state, body, etc.
        """
        # Use search API for query, or issues API for listing
        if query:
            search_query = f"repo:{repo} {query}"
            if state != "all":
                search_query += f" state:{state}"

            endpoint = "/search/issues"
            params = {"q": search_query, "per_page": limit}

            data = self._get(endpoint, params)
            items = data.get("items", [])
        else:
            endpoint = f"/repos/{repo}/issues"
            params = {"state": state, "per_page": limit}

            items = self._get(endpoint, params)

        return [
            {
                "number": item["number"],
                "title": item["title"],
                "state": item["state"],
                "is_pr": "pull_request" in item,
                "body": (item.get("body") or "")[:500],  # Truncate body
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
                "user": item["user"]["login"],
                "labels": [label["name"] for label in item.get("labels", [])],
                "url": item["html_url"]
            }
            for item in items
        ]

    def get_commits(
        self,
        repo: str,
        path: str = None,
        branch: str = "main",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent commits from a repository.

        Args:
            repo: Repository in "owner/repo" format
            path: Filter commits by path (optional)
            branch: Branch name (default: main)
            limit: Maximum commits to return

        Returns:
            List of commit dicts with sha, message, author, date
        """
        endpoint = f"/repos/{repo}/commits"
        params = {"sha": branch, "per_page": limit}
        if path:
            params["path"] = path

        data = self._get(endpoint, params)

        return [
            {
                "sha": commit["sha"][:7],
                "message": commit["commit"]["message"].split("\n")[0][:100],  # First line, truncated
                "author": commit["commit"]["author"]["name"],
                "date": commit["commit"]["author"]["date"],
                "url": commit["html_url"]
            }
            for commit in data
        ]

    def get_repo_info(self, repo: str) -> Dict[str, Any]:
        """
        Get basic repository information.

        Args:
            repo: Repository in "owner/repo" format

        Returns:
            Dict with description, stars, forks, language, etc.
        """
        endpoint = f"/repos/{repo}"
        data = self._get(endpoint)

        return {
            "name": data["full_name"],
            "description": data.get("description", ""),
            "language": data.get("language", "Unknown"),
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "open_issues": data["open_issues_count"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "default_branch": data["default_branch"],
            "private": data["private"],
            "url": data["html_url"]
        }

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Dict with remaining requests, reset time, etc.
        """
        endpoint = "/rate_limit"
        data = self._get(endpoint)

        core = data.get("resources", {}).get("core", {})
        return {
            "limit": core.get("limit", 60),
            "remaining": core.get("remaining", 0),
            "reset": datetime.fromtimestamp(core.get("reset", 0)).strftime("%H:%M:%S"),
            "used": core.get("used", 0)
        }

    def format_for_kay(self, content: str, source: str, max_chars: int = 5000) -> str:
        """
        Format content for inclusion in Kay's context.

        Args:
            content: Raw content
            source: Source description (e.g., "owner/repo/path")
            max_chars: Maximum characters to include

        Returns:
            Formatted string for Kay's context
        """
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... [truncated, {len(content) - max_chars} more chars]"

        return f"--- GitHub: {source} ---\n{content}\n--- End GitHub content ---"


# Custom exceptions
class GitHubError(Exception):
    """Base exception for GitHub API errors."""
    pass


class GitHubNotFoundError(GitHubError):
    """Resource not found (404)."""
    pass


class GitHubAuthError(GitHubError):
    """Authentication error (401)."""
    pass


class GitHubRateLimitError(GitHubError):
    """Rate limit exceeded (403)."""
    pass


# Singleton instance
_github_service: Optional[GitHubService] = None


def get_github_service() -> GitHubService:
    """Get or create the GitHub service singleton."""
    global _github_service
    if _github_service is None:
        _github_service = GitHubService()
    return _github_service


def handle_github_command(command: str) -> str:
    """
    Handle /github commands from Kay's interface.

    Usage:
        /github read owner/repo path/to/file.py [branch]
        /github ls owner/repo [path] [branch]
        /github readme owner/repo [branch]
        /github issues owner/repo [query] [state]
        /github commits owner/repo [path] [limit]
        /github info owner/repo
        /github status

    Args:
        command: The full command string after "/github "

    Returns:
        Formatted response string
    """
    github = get_github_service()
    parts = command.strip().split()

    if not parts:
        return _github_help()

    action = parts[0].lower()

    try:
        if action == "read" and len(parts) >= 3:
            repo = parts[1]
            path = parts[2]
            branch = parts[3] if len(parts) > 3 else "main"
            content = github.get_file_contents(repo, path, branch)
            return github.format_for_kay(content, f"{repo}/{path}")

        elif action in ("ls", "list", "dir") and len(parts) >= 2:
            repo = parts[1]
            path = parts[2] if len(parts) > 2 else ""
            branch = parts[3] if len(parts) > 3 else "main"
            items = github.list_directory(repo, path, branch)

            lines = [f"Directory listing: {repo}/{path or '(root)'}"]
            for item in items:
                icon = "[DIR]" if item["type"] == "dir" else "[FILE]"
                size = f" ({item['size']} bytes)" if item["type"] == "file" else ""
                lines.append(f"  {icon} {item['name']}{size}")
            return "\n".join(lines)

        elif action == "readme" and len(parts) >= 2:
            repo = parts[1]
            branch = parts[2] if len(parts) > 2 else "main"
            content = github.get_readme(repo, branch)
            return github.format_for_kay(content, f"{repo}/README")

        elif action == "issues" and len(parts) >= 2:
            repo = parts[1]
            query = parts[2] if len(parts) > 2 else ""
            state = parts[3] if len(parts) > 3 else "all"
            issues = github.search_issues(repo, query, state)

            if not issues:
                return f"No issues found in {repo}" + (f" matching '{query}'" if query else "")

            lines = [f"Issues in {repo}:" + (f" (matching '{query}')" if query else "")]
            for issue in issues:
                pr_tag = " [PR]" if issue["is_pr"] else ""
                state_tag = f"[{issue['state']}]"
                lines.append(f"  #{issue['number']} {state_tag}{pr_tag} {issue['title']}")
                if issue["labels"]:
                    lines.append(f"    Labels: {', '.join(issue['labels'])}")
            return "\n".join(lines)

        elif action == "commits" and len(parts) >= 2:
            repo = parts[1]
            path = parts[2] if len(parts) > 2 and not parts[2].isdigit() else None
            limit = int(parts[-1]) if parts[-1].isdigit() else 10
            commits = github.get_commits(repo, path, limit=limit)

            lines = [f"Recent commits in {repo}:" + (f" (path: {path})" if path else "")]
            for commit in commits:
                lines.append(f"  {commit['sha']} - {commit['message']}")
                lines.append(f"    by {commit['author']} on {commit['date'][:10]}")
            return "\n".join(lines)

        elif action == "info" and len(parts) >= 2:
            repo = parts[1]
            info = github.get_repo_info(repo)

            lines = [
                f"Repository: {info['name']}",
                f"Description: {info['description'] or '(none)'}",
                f"Language: {info['language']}",
                f"Stars: {info['stars']} | Forks: {info['forks']} | Open Issues: {info['open_issues']}",
                f"Default branch: {info['default_branch']}",
                f"Private: {info['private']}",
                f"URL: {info['url']}"
            ]
            return "\n".join(lines)

        elif action == "status":
            status = github.get_rate_limit_status()
            return (
                f"GitHub API Rate Limit Status:\n"
                f"  Remaining: {status['remaining']}/{status['limit']}\n"
                f"  Used: {status['used']}\n"
                f"  Resets at: {status['reset']}"
            )

        else:
            return _github_help()

    except GitHubNotFoundError as e:
        return f"[GitHub] Not found: {e}"
    except GitHubAuthError as e:
        return f"[GitHub] Authentication error: {e}"
    except GitHubRateLimitError as e:
        return f"[GitHub] Rate limit exceeded: {e}"
    except GitHubError as e:
        return f"[GitHub] Error: {e}"
    except Exception as e:
        return f"[GitHub] Unexpected error: {e}"


def _github_help() -> str:
    """Return help text for GitHub commands."""
    return """GitHub Commands:
  /github read <owner/repo> <path> [branch]    - Read a file
  /github ls <owner/repo> [path] [branch]      - List directory contents
  /github readme <owner/repo> [branch]         - Get README
  /github issues <owner/repo> [query] [state]  - Search issues/PRs
  /github commits <owner/repo> [path] [limit]  - Recent commits
  /github info <owner/repo>                    - Repository info
  /github status                               - Rate limit status

Examples:
  /github read anthropics/claude-code README.md
  /github ls anthropics/claude-code src
  /github issues anthropics/claude-code "memory bug" open
  /github commits anthropics/claude-code 10"""
