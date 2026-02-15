"""
Locust load testing file for BugsTracker API.

Usage:
    locust -f locustfile.py --host=http://localhost:8000
    Then open http://localhost:8089 in browser

Or headless:
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 5m --headless
"""

from locust import HttpUser, task, between, SequentialTaskSet
import random
import json


class AuthenticatedUser(HttpUser):
    """Base class for authenticated API users."""

    wait_time = between(1, 3)
    token = None
    organization_id = None
    project_id = None
    issue_ids = []

    def on_start(self):
        """Login before starting tasks."""
        # Login
        response = self.client.post("/api/v1/auth/login/", json={
            "email": "loadtest@example.com",
            "password": "loadtestpass123"
        }, name="/api/v1/auth/login")

        if response.status_code == 200:
            data = response.json().get('data', {})
            self.token = data.get('access')

            if self.token:
                self.client.headers.update({
                    'Authorization': f'Bearer {self.token}'
                })

                # Get user's organization and project
                self._setup_context()

    def _setup_context(self):
        """Set up organization and project context."""
        # Get organizations
        response = self.client.get("/api/v1/organizations/")
        if response.status_code == 200:
            orgs = response.json().get('results', [])
            if orgs:
                self.organization_id = orgs[0]['id']

                # Get projects
                response = self.client.get("/api/v1/projects/")
                if response.status_code == 200:
                    projects = response.json().get('results', [])
                    if projects:
                        self.project_id = projects[0]['id']


class IssueManagementUser(AuthenticatedUser):
    """User that performs issue management tasks."""

    @task(5)
    def list_issues(self):
        """List issues (most common operation)."""
        self.client.get(
            "/api/v1/issues/",
            params={
                'page': random.randint(1, 5),
                'page_size': 50
            },
            name="/api/v1/issues/ (list)"
        )

    @task(3)
    def filter_issues(self):
        """Filter issues by various criteria."""
        filters = [
            {'status': 'in_progress'},
            {'priority': 'high'},
            {'issue_type': 'bug'},
            {'ordering': '-created_at'},
        ]
        filter_params = random.choice(filters)

        self.client.get(
            "/api/v1/issues/",
            params=filter_params,
            name="/api/v1/issues/ (filtered)"
        )

    @task(2)
    def search_issues(self):
        """Search issues with full-text search."""
        search_terms = ['authentication', 'bug', 'feature', 'performance']

        self.client.get(
            "/api/v1/issues/",
            params={'search': random.choice(search_terms)},
            name="/api/v1/issues/ (search)"
        )

    @task(1)
    def create_issue(self):
        """Create a new issue."""
        if not self.project_id:
            return

        issue_data = {
            'project': self.project_id,
            'summary': f'Load test issue {random.randint(1, 10000)}',
            'description': 'This is a load test issue',
            'issue_type': random.choice(['task', 'bug', 'story']),
            'priority': random.choice(['low', 'medium', 'high']),
        }

        response = self.client.post(
            "/api/v1/issues/",
            json=issue_data,
            name="/api/v1/issues/ (create)"
        )

        if response.status_code == 201:
            issue_id = response.json().get('data', {}).get('id')
            if issue_id:
                self.issue_ids.append(issue_id)

    @task(2)
    def get_issue_detail(self):
        """Get issue details."""
        if not self.issue_ids:
            # Get some issues first
            response = self.client.get("/api/v1/issues/")
            if response.status_code == 200:
                results = response.json().get('results', [])
                self.issue_ids = [issue['id'] for issue in results[:10]]

        if self.issue_ids:
            issue_id = random.choice(self.issue_ids)
            self.client.get(
                f"/api/v1/issues/{issue_id}/",
                name="/api/v1/issues/{id}/"
            )

    @task(1)
    def update_issue(self):
        """Update an issue."""
        if not self.issue_ids:
            return

        issue_id = random.choice(self.issue_ids)
        update_data = {
            'priority': random.choice(['low', 'medium', 'high', 'critical']),
            'status': random.choice(['to_do', 'in_progress', 'done']),
        }

        self.client.patch(
            f"/api/v1/issues/{issue_id}/",
            json=update_data,
            name="/api/v1/issues/{id}/ (update)"
        )


class ProjectManagementUser(AuthenticatedUser):
    """User that manages projects."""

    @task(10)
    def list_projects(self):
        """List projects."""
        self.client.get(
            "/api/v1/projects/",
            name="/api/v1/projects/ (list)"
        )

    @task(5)
    def get_project_detail(self):
        """Get project details."""
        if self.project_id:
            self.client.get(
                f"/api/v1/projects/{self.project_id}/",
                name="/api/v1/projects/{id}/"
            )

    @task(3)
    def list_project_members(self):
        """List project members."""
        if self.project_id:
            self.client.get(
                f"/api/v1/projects/{self.project_id}/members/",
                name="/api/v1/projects/{id}/members/"
            )


class SearchUser(AuthenticatedUser):
    """User that performs searches."""

    @task(5)
    def jql_search(self):
        """Search with JQL."""
        jql_queries = [
            'project="TEST" AND status="in_progress"',
            'priority=high AND assignee=currentUser()',
            'type=bug AND priority IN (high, critical)',
            'created >= -7d',
        ]

        self.client.get(
            "/api/v1/search/",
            params={'jql': random.choice(jql_queries)},
            name="/api/v1/search/ (JQL)"
        )

    @task(3)
    def full_text_search(self):
        """Full-text search."""
        search_terms = ['authentication', 'bug', 'api', 'database', 'performance']

        self.client.get(
            "/api/v1/search/",
            params={'q': random.choice(search_terms)},
            name="/api/v1/search/ (full-text)"
        )


class ReadOnlyUser(AuthenticatedUser):
    """User that only reads data (no writes)."""

    @task(5)
    def list_issues(self):
        """List issues."""
        self.client.get("/api/v1/issues/", name="/api/v1/issues/")

    @task(3)
    def list_projects(self):
        """List projects."""
        self.client.get("/api/v1/projects/", name="/api/v1/projects/")

    @task(2)
    def get_notifications(self):
        """Get notifications."""
        self.client.get("/api/v1/notifications/", name="/api/v1/notifications/")

    @task(1)
    def get_audit_logs(self):
        """Get audit logs."""
        self.client.get("/api/v1/audit-logs/", name="/api/v1/audit-logs/")


class WorkflowSequence(SequentialTaskSet):
    """Sequential workflow: create project → create issue → update → complete."""

    @task
    def create_project(self):
        """Step 1: Create a project."""
        if not self.user.organization_id:
            self.interrupt()
            return

        project_data = {
            'organization': self.user.organization_id,
            'name': f'Load Test Project {random.randint(1, 10000)}',
            'key': f'LT{random.randint(1, 999)}',
            'description': 'Load test project',
        }

        response = self.client.post(
            "/api/v1/projects/",
            json=project_data,
            name="Workflow: Create Project"
        )

        if response.status_code == 201:
            self.user.project_id = response.json().get('data', {}).get('id')

    @task
    def create_issue(self):
        """Step 2: Create an issue in the project."""
        if not self.user.project_id:
            self.interrupt()
            return

        issue_data = {
            'project': self.user.project_id,
            'summary': f'Workflow test issue {random.randint(1, 10000)}',
            'description': 'Workflow test issue',
            'issue_type': 'task',
            'priority': 'medium',
        }

        response = self.client.post(
            "/api/v1/issues/",
            json=issue_data,
            name="Workflow: Create Issue"
        )

        if response.status_code == 201:
            issue_id = response.json().get('data', {}).get('id')
            self.user.issue_ids.append(issue_id)

    @task
    def update_issue(self):
        """Step 3: Update the issue."""
        if not self.user.issue_ids:
            self.interrupt()
            return

        issue_id = self.user.issue_ids[-1]
        update_data = {
            'status': 'in_progress',
            'priority': 'high',
        }

        self.client.patch(
            f"/api/v1/issues/{issue_id}/",
            json=update_data,
            name="Workflow: Update Issue"
        )

    @task
    def complete_issue(self):
        """Step 4: Complete the issue."""
        if not self.user.issue_ids:
            self.interrupt()
            return

        issue_id = self.user.issue_ids[-1]
        update_data = {
            'status': 'done',
        }

        self.client.patch(
            f"/api/v1/issues/{issue_id}/",
            json=update_data,
            name="Workflow: Complete Issue"
        )


class CompleteWorkflowUser(AuthenticatedUser):
    """User that performs complete workflows."""

    tasks = [WorkflowSequence]
    wait_time = between(2, 5)


# User distribution for realistic load
# 60% issue management, 20% project management, 10% search, 10% read-only
class LoadTestUsers(HttpUser):
    """Mixed user types with realistic distribution."""

    tasks = {
        IssueManagementUser: 6,
        ProjectManagementUser: 2,
        SearchUser: 1,
        ReadOnlyUser: 1,
    }
    wait_time = between(1, 3)
