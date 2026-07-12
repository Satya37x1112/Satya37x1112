"""
update_stats.py — GitHub Profile Stats Automation for Satya37x1112

Dynamically queries the GitHub GraphQL API to gather profile statistics
(commits, stars, repos, LOC, followers) and writes them into SVG dashboard
files (dark_mode.svg and light_mode.svg).

Originally based on Andrew6rant's today.py, refactored and tailored for
the Satya37x1112 profile.

─────────────────────────────────────────────────────────────────────────
HOW TO PROVISION THE GITHUB PERSONAL ACCESS TOKEN (ACCESS_TOKEN):

1. Go to https://github.com/settings/tokens?type=beta
2. Click "Generate new token" (Fine-grained personal access token).
3. Give the token a descriptive name, e.g. "Profile Stats Automation".
4. Set expiration as desired (or "No expiration" for long-running CI).
5. Under "Repository access", select "All repositories".
6. Under "Account permissions", enable:
      - Followers    → Read-only
      - Starring     → Read-only
      - Watching     → Read-only
7. Under "Repository permissions", enable:
      - Commit statuses → Read-only
      - Contents        → Read-only
      - Metadata        → Read-only
8. Click "Generate token" and copy the token value.
9. In your GitHub repository, go to Settings → Secrets and variables →
   Actions → "New repository secret".
10. Name the secret  METRICS_TOKEN  and paste the token value.

The GitHub Actions workflow (.github/workflows/main.yml) injects this
secret as the ACCESS_TOKEN environment variable at runtime:
    env:
      ACCESS_TOKEN: ${{ secrets.METRICS_TOKEN }}
      USER_NAME: 'Satya37x1112'

For local development/testing, export the variables in your shell:
    export ACCESS_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    export USER_NAME="Satya37x1112"
─────────────────────────────────────────────────────────────────────────
"""

import datetime
import hashlib
import os
import time

import requests
from dateutil import relativedelta
from lxml import etree


# ─── Configuration ────────────────────────────────────────────────────────────
# ACCESS_TOKEN: Fine-grained GitHub Personal Access Token (see docstring above).
# Must be set as an environment variable before running this script.
HEADERS = {"authorization": "token " + os.environ["ACCESS_TOKEN"]}

# USER_NAME: Your GitHub username. Set via environment variable so the same
# script can be reused across profiles without code changes.
USER_NAME = os.environ.get("USER_NAME", "Satya37x1112")

# Tracks how many GraphQL API calls each function makes (for debugging/logging).
QUERY_COUNT = {
    "user_getter": 0,
    "follower_getter": 0,
    "graph_repos_stars": 0,
    "recursive_loc": 0,
    "graph_commits": 0,
    "loc_query": 0,
}

# Global variable set at runtime by user_getter(); used to filter commits.
OWNER_ID = None


# ─── Utility Functions ───────────────────────────────────────────────────────


def daily_readme(birthday):
    """
    Returns a human-readable string showing elapsed time since birth.
    Example: '22 years, 3 months, 26 days'
    Appends a 🎂 emoji on the exact birthday.
    """
    diff = relativedelta.relativedelta(datetime.datetime.today(), birthday)
    return "{} {}, {} {}, {} {}{}".format(
        diff.years,
        "year" + _pluralize(diff.years),
        diff.months,
        "month" + _pluralize(diff.months),
        diff.days,
        "day" + _pluralize(diff.days),
        " 🎂" if (diff.months == 0 and diff.days == 0) else "",
    )


def _pluralize(unit):
    """Returns 's' if the unit is not 1, for grammatical correctness."""
    return "s" if unit != 1 else ""


# ─── GitHub GraphQL API Functions ─────────────────────────────────────────────


def simple_request(func_name, query, variables):
    """
    Sends a GraphQL POST request to GitHub's API.
    Returns the response on success (HTTP 200).
    Raises Exception with diagnostics on failure.
    """
    request = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
    )
    if request.status_code == 200:
        return request
    raise Exception(
        func_name,
        " has failed with a",
        request.status_code,
        request.text,
        QUERY_COUNT,
    )


def graph_commits(start_date, end_date):
    """
    Returns total contribution count between start_date and end_date
    using the GitHub contributionsCollection API.
    """
    _query_count("graph_commits")
    query = """
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                contributionCalendar {
                    totalContributions
                }
            }
        }
    }"""
    variables = {"start_date": start_date, "end_date": end_date, "login": USER_NAME}
    request = simple_request(graph_commits.__name__, query, variables)
    return int(
        request.json()["data"]["user"]["contributionsCollection"][
            "contributionCalendar"
        ]["totalContributions"]
    )


def graph_repos_stars(count_type, owner_affiliation, cursor=None):
    """
    Returns total repository count OR total star count, depending on count_type.
    Supports cursor-based pagination for >100 repositories.

    Args:
        count_type: 'repos' for repository count, 'stars' for star count.
        owner_affiliation: List like ['OWNER'], ['OWNER', 'COLLABORATOR', ...].
        cursor: Pagination cursor (None for first page).
    """
    _query_count("graph_repos_stars")
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            stargazers {
                                totalCount
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }"""
    variables = {
        "owner_affiliation": owner_affiliation,
        "login": USER_NAME,
        "cursor": cursor,
    }
    request = simple_request(graph_repos_stars.__name__, query, variables)
    if request.status_code == 200:
        if count_type == "repos":
            return request.json()["data"]["user"]["repositories"]["totalCount"]
        elif count_type == "stars":
            return _stars_counter(
                request.json()["data"]["user"]["repositories"]["edges"]
            )


def recursive_loc(
    owner,
    repo_name,
    data,
    cache_comment,
    addition_total=0,
    deletion_total=0,
    my_commits=0,
    cursor=None,
):
    """
    Fetches 100 commits at a time from a repository via cursor pagination.
    Only counts lines of code (additions/deletions) from commits authored by OWNER_ID.
    """
    _query_count("recursive_loc")
    query = """
    query ($repo_name: String!, $owner: String!, $cursor: String) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit {
                                        committedDate
                                    }
                                    author {
                                        user {
                                            id
                                        }
                                    }
                                    deletions
                                    additions
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }
    }"""
    variables = {"repo_name": repo_name, "owner": owner, "cursor": cursor}
    # Manual request (not simple_request) so we can save the cache before crashing.
    request = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
    )
    if request.status_code == 200:
        if request.json()["data"]["repository"]["defaultBranchRef"] is not None:
            return _loc_counter_one_repo(
                owner,
                repo_name,
                data,
                cache_comment,
                request.json()["data"]["repository"]["defaultBranchRef"]["target"][
                    "history"
                ],
                addition_total,
                deletion_total,
                my_commits,
            )
        else:
            return 0  # Empty repository — no commits to count
    # Save partial data before raising so progress isn't lost.
    _force_close_file(data, cache_comment)
    if request.status_code == 403:
        raise Exception(
            "Too many requests in a short amount of time!\n"
            "You've hit the non-documented anti-abuse limit!"
        )
    raise Exception(
        "recursive_loc() has failed with a",
        request.status_code,
        request.text,
        QUERY_COUNT,
    )


def _loc_counter_one_repo(
    owner,
    repo_name,
    data,
    cache_comment,
    history,
    addition_total,
    deletion_total,
    my_commits,
):
    """
    Processes one page of commit history. Accumulates LOC only for commits
    authored by OWNER_ID. Recurses via recursive_loc if more pages exist.
    """
    for node in history["edges"]:
        if node["node"]["author"]["user"] == OWNER_ID:
            my_commits += 1
            addition_total += node["node"]["additions"]
            deletion_total += node["node"]["deletions"]

    if history["edges"] == [] or not history["pageInfo"]["hasNextPage"]:
        return addition_total, deletion_total, my_commits
    else:
        return recursive_loc(
            owner,
            repo_name,
            data,
            cache_comment,
            addition_total,
            deletion_total,
            my_commits,
            history["pageInfo"]["endCursor"],
        )


def loc_query(owner_affiliation, comment_size=0, force_cache=False, cursor=None, _edges=None):
    """
    Queries all repositories the user has access to (filtered by owner_affiliation).
    Fetches 60 repos per page (larger queries can cause 502 timeouts).
    Returns [total_additions, total_deletions, net_loc, cached_bool].

    Note: _edges uses None sentinel instead of a mutable default list to avoid
    the classic Python mutable-default-argument bug.
    """
    if _edges is None:
        _edges = []

    _query_count("loc_query")
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
            edges {
                node {
                    ... on Repository {
                        nameWithOwner
                        defaultBranchRef {
                            target {
                                ... on Commit {
                                    history {
                                        totalCount
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }"""
    variables = {
        "owner_affiliation": owner_affiliation,
        "login": USER_NAME,
        "cursor": cursor,
    }
    request = simple_request(loc_query.__name__, query, variables)
    if request.json()["data"]["user"]["repositories"]["pageInfo"]["hasNextPage"]:
        _edges += request.json()["data"]["user"]["repositories"]["edges"]
        return loc_query(
            owner_affiliation,
            comment_size,
            force_cache,
            request.json()["data"]["user"]["repositories"]["pageInfo"]["endCursor"],
            _edges,
        )
    else:
        return _cache_builder(
            _edges + request.json()["data"]["user"]["repositories"]["edges"],
            comment_size,
            force_cache,
        )


# ─── Cache Management ────────────────────────────────────────────────────────


def _cache_builder(edges, comment_size, force_cache, loc_add=0, loc_del=0):
    """
    Checks each repository to see if its commit count has changed since last cache.
    If changed, re-runs recursive_loc on that repo to refresh the LOC count.
    Returns [total_additions, total_deletions, net_loc, cached_bool].
    """
    filename = (
        "cache/" + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest() + ".txt"
    )
    try:
        with open(filename, "r") as f:
            data = f.readlines()
    except FileNotFoundError:
        data = []
        if comment_size > 0:
            for _ in range(comment_size):
                data.append(
                    "This line is a comment block. Write whatever you want here.\n"
                )
        with open(filename, "w") as f:
            f.writelines(data)

    if len(data) - comment_size != len(edges) or force_cache:
        _flush_cache(edges, filename, comment_size)
        with open(filename, "r") as f:
            data = f.readlines()

    cache_comment = data[:comment_size]  # Preserve the comment header block
    data = data[comment_size:]  # Working data (one line per repo)

    for index in range(len(edges)):
        repo_hash, commit_count, *__ = data[index].split()
        if repo_hash == hashlib.sha256(
            edges[index]["node"]["nameWithOwner"].encode("utf-8")
        ).hexdigest():
            try:
                if (
                    int(commit_count)
                    != edges[index]["node"]["defaultBranchRef"]["target"]["history"][
                        "totalCount"
                    ]
                ):
                    # Commit count changed → re-scan this repo's LOC
                    owner, repo_name = edges[index]["node"]["nameWithOwner"].split("/")
                    loc = recursive_loc(owner, repo_name, data, cache_comment)
                    data[index] = (
                        repo_hash
                        + " "
                        + str(
                            edges[index]["node"]["defaultBranchRef"]["target"][
                                "history"
                            ]["totalCount"]
                        )
                        + " "
                        + str(loc[2])
                        + " "
                        + str(loc[0])
                        + " "
                        + str(loc[1])
                        + "\n"
                    )
            except TypeError:
                # Empty repo (no default branch / no history)
                data[index] = repo_hash + " 0 0 0 0\n"

    with open(filename, "w") as f:
        f.writelines(cache_comment)
        f.writelines(data)

    for line in data:
        loc = line.split()
        loc_add += int(loc[3])
        loc_del += int(loc[4])

    return [loc_add, loc_del, loc_add - loc_del, True]


def _flush_cache(edges, filename, comment_size):
    """
    Wipes and rebuilds the cache file when repository count changes
    or the cache is first created.
    """
    with open(filename, "r") as f:
        data = []
        if comment_size > 0:
            data = f.readlines()[:comment_size]
    with open(filename, "w") as f:
        f.writelines(data)
        for node in edges:
            f.write(
                hashlib.sha256(
                    node["node"]["nameWithOwner"].encode("utf-8")
                ).hexdigest()
                + " 0 0 0 0\n"
            )


def _force_close_file(data, cache_comment):
    """
    Emergency save: writes whatever partial data exists to the cache file
    before the program crashes. Prevents total data loss on API errors.
    """
    filename = (
        "cache/" + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest() + ".txt"
    )
    with open(filename, "w") as f:
        f.writelines(cache_comment)
        f.writelines(data)
    print(
        "There was an error while writing to the cache file. The file,",
        filename,
        "has had the partial data saved and closed.",
    )


# ─── Star / Commit / Follower Counters ───────────────────────────────────────


def _stars_counter(data):
    """Counts total stars across all owned repositories."""
    total_stars = 0
    for node in data:
        total_stars += node["node"]["stargazers"]["totalCount"]
    return total_stars


def commit_counter(comment_size):
    """
    Reads the cache file and sums up the commit counts for all repositories.
    The cache file is created/maintained by _cache_builder().
    """
    total_commits = 0
    filename = (
        "cache/" + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest() + ".txt"
    )
    with open(filename, "r") as f:
        data = f.readlines()
    data = data[comment_size:]  # Skip comment header
    for line in data:
        total_commits += int(line.split()[2])
    return total_commits


def user_getter(username):
    """
    Returns the authenticated user's account ID (for commit attribution)
    and the account creation timestamp.
    """
    _query_count("user_getter")
    query = """
    query($login: String!){
        user(login: $login) {
            id
            createdAt
        }
    }"""
    variables = {"login": username}
    request = simple_request(user_getter.__name__, query, variables)
    return (
        {"id": request.json()["data"]["user"]["id"]},
        request.json()["data"]["user"]["createdAt"],
    )


def follower_getter(username):
    """Returns the total follower count for the given username."""
    _query_count("follower_getter")
    query = """
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }"""
    request = simple_request(follower_getter.__name__, query, {"login": username})
    return int(request.json()["data"]["user"]["followers"]["totalCount"])


# ─── SVG Rendering ───────────────────────────────────────────────────────────


def svg_overwrite(
    filename, age_data, uptime_data, commit_data, star_data, repo_data,
    contrib_data, follower_data, loc_data,
):
    """
    Parses a neofetch-style SVG file and updates text elements with fresh statistics.
    Uses monospace-justified dots for perfect alignment.
    """
    tree = etree.parse(filename)
    root = tree.getroot()

    # Set age and uptime values (no length justification needed)
    justify_format(root, "age_data", age_data)
    justify_format(root, "uptime_data", uptime_data)

    # Justify Repo and Star stats
    justify_format(root, "repo_data", repo_data, 6)
    justify_format(root, "star_data", star_data, 14)
    justify_format(root, "contrib_data", contrib_data)  # no length justification needed

    # Justify Commits and Followers
    justify_format(root, "commit_data", commit_data, 23)
    justify_format(root, "follower_data", follower_data, 10)

    # Justify Lines of Code (LOC)
    justify_format(root, "loc_data", loc_data[2], 9)
    justify_format(root, "loc_add", loc_data[0])  # no length justification needed
    justify_format(root, "loc_del", loc_data[1], 7)

    tree.write(filename, encoding="utf-8", xml_declaration=True)


def justify_format(root, element_id, new_text, length=0):
    """
    Updates the text of the element, and modifies the amount of dots in the
    corresponding dot leader element (f"{element_id}_dots") to justify the alignment.
    """
    if isinstance(new_text, int):
        new_text = "{:,}".format(new_text)
    new_text = str(new_text)
    _set_text(root, element_id, new_text)
    
    if length > 0:
        just_len = max(0, length - len(new_text))
        if just_len <= 2:
            dot_map = {0: '', 1: ' ', 2: '. '}
            dot_string = dot_map[just_len]
        else:
            dot_string = ' ' + ('.' * just_len) + ' '
        _set_text(root, f"{element_id}_dots", dot_string)


def _set_text(root, element_id, new_text):
    """
    Locates an SVG element by its 'id' attribute and replaces its text content.
    Silently skips if the element is not found (graceful degradation).
    """
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = str(new_text)


def compute_uptime(acc_date_str):
    """
    Computes account uptime from the GitHub account creation date.
    Returns a human-readable string like '5 years, 8 months'.
    """
    created = datetime.datetime.strptime(acc_date_str[:10], "%Y-%m-%d")
    diff = relativedelta.relativedelta(datetime.datetime.today(), created)
    parts = []
    if diff.years:
        parts.append(f"{diff.years} yr{'s' if diff.years != 1 else ''}")
    if diff.months:
        parts.append(f"{diff.months} mo{'s' if diff.months != 1 else ''}")
    if diff.days and not diff.years:
        parts.append(f"{diff.days} day{'s' if diff.days != 1 else ''}")
    return ", ".join(parts) if parts else "< 1 month"


# ─── Performance / Logging Helpers ────────────────────────────────────────────


def _query_count(funct_id):
    """Increments the API call counter for the given function."""
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1


def perf_counter(funct, *args):
    """
    Times a function call and returns (result, elapsed_seconds).
    """
    start = time.perf_counter()
    funct_return = funct(*args)
    return funct_return, time.perf_counter() - start


def formatter(query_type, difference, funct_return=False, whitespace=0):
    """
    Pretty-prints a timing result for a query.
    Returns formatted result if whitespace > 0, otherwise returns raw result.
    """
    print("{:<23}".format("   " + query_type + ":"), sep="", end="")
    if difference > 1:
        print("{:>12}".format("%.4f" % difference + " s "))
    else:
        print("{:>12}".format("%.4f" % (difference * 1000) + " ms"))
    if whitespace:
        return f"{'{:,}'.format(funct_return): <{whitespace}}"
    return funct_return


# ─── Main Entry Point ────────────────────────────────────────────────────────


if __name__ == "__main__":
    """
    Satya37x1112 Profile Stats Automation
    Refactored from Andrew6rant's today.py (2022-2025)
    """
    print("Calculation times:")

    # ── Step 1: Fetch account metadata ────────────────────────────────────
    # Returns the user's GraphQL node ID (for commit filtering) and
    # the account creation timestamp.
    user_data, user_time = perf_counter(user_getter, USER_NAME)
    OWNER_ID, acc_date = user_data
    formatter("account data", user_time)

    # ── Step 2: Calculate age from birthday ───────────────────────────────
    # UPDATE THIS DATE to your actual birthday: datetime.datetime(YYYY, M, D)
    # Currently set to May 25, 2005.
    age_data, age_time = perf_counter(daily_readme, datetime.datetime(2005, 5, 25))
    formatter("age calculation", age_time)

    # ── Step 3: Count lines of code across all accessible repos ───────────
    # comment_size=7 means the first 7 lines of the cache file are comments.
    total_loc, loc_time = perf_counter(
        loc_query, ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"], 7
    )
    if total_loc[-1]:
        formatter("LOC (cached)", loc_time)
    else:
        formatter("LOC (no cache)", loc_time)

    # ── Step 4: Gather remaining stats ────────────────────────────────────
    commit_data, commit_time = perf_counter(commit_counter, 7)
    star_data, star_time = perf_counter(graph_repos_stars, "stars", ["OWNER"])
    repo_data, repo_time = perf_counter(graph_repos_stars, "repos", ["OWNER"])
    contrib_data, contrib_time = perf_counter(
        graph_repos_stars, "repos", ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"]
    )
    follower_data, follower_time = perf_counter(follower_getter, USER_NAME)

    # ── Step 5: Format LOC values with commas ─────────────────────────────
    for index in range(len(total_loc) - 1):
        total_loc[index] = "{:,}".format(total_loc[index])

    # ── Step 6: Compute account uptime ─────────────────────────────────────
    uptime_data = compute_uptime(acc_date)

    # ── Step 7: Write stats into both SVG dashboard files ─────────────────
    for svg_file in ("dark_mode.svg", "light_mode.svg"):
        svg_overwrite(
            svg_file,
            age_data,
            uptime_data,
            commit_data,
            star_data,
            repo_data,
            contrib_data,
            follower_data,
            total_loc[:-1],
        )

    # ── Step 8: Print performance summary ─────────────────────────────────
    total_time = (
        user_time
        + age_time
        + loc_time
        + commit_time
        + star_time
        + repo_time
        + contrib_time
    )
    # Move cursor up to overwrite the header line with the total time
    print(
        "\033[F\033[F\033[F\033[F\033[F\033[F\033[F\033[F",
        "{:<21}".format("Total function time:"),
        "{:>11}".format("%.4f" % total_time),
        " s \033[E\033[E\033[E\033[E\033[E\033[E\033[E\033[E",
        sep="",
    )

    print(
        "Total GitHub GraphQL API calls:",
        "{:>3}".format(sum(QUERY_COUNT.values())),
    )
    for funct_name, count in QUERY_COUNT.items():
        print("{:<28}".format("   " + funct_name + ":"), "{:>6}".format(count))
