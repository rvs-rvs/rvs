"""Log command implementation."""
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, List
from .base import BaseCommand

class LogCommand(BaseCommand):
    """Show commit history."""
    
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register log command parser."""
        parser = subparsers.add_parser('log', help='Show commit history')
        parser.add_argument("--max-count", type=int, default=10, help="Maximum number of commits to show")
        parser.add_argument("-n", type=int, dest="max_count", help="Maximum number of commits to show")
        parser.add_argument("-1", action="store_const", const=1, dest="max_count", help="Show only one commit")
        parser.add_argument("--oneline", action="store_true", help="Show each commit on a single line")
        parser.add_argument("--graph", action="store_true", help="Show commit graph")
        parser.add_argument("--pretty", choices=["oneline", "short", "medium", "full"], help="Pretty-print format")
        return parser
    
    def execute_from_args(self, args: Any) -> None:
        """Execute log command from parsed arguments."""
        self.execute(args.max_count, args.oneline, args.graph)
    
    def execute(self, max_count: int = 10, oneline: bool = False, graph: bool = False) -> None:
        """Show commit history."""
        self.repo.log(max_count, oneline, graph)
    
    def _print_commit_graph(self, commits: List[dict], current_branch: str):
        """Print commit history with ASCII graph."""
        if not commits:
            return
        
        # Build commit graph
        graph_lines = []
        commit_positions = {}
        branch_colors = {}
        color_index = 0
        
        # Assign positions to commits
        for i, commit in enumerate(commits):
            commit_hash = commit['hash']
            commit_positions[commit_hash] = i
        
        # Draw graph for each commit
        for i, commit in enumerate(commits):
            commit_hash = commit['hash']
            is_head = i == 0
            
            # Start with empty line
            line = [" "] * len(commits)
            
            # Mark current commit
            line[i] = "*"
            
            # Draw connections to parents
            parents = commit.get('parents', [])
            if parents:
                for parent_hash in parents:
                    if parent_hash in commit_positions:
                        parent_pos = commit_positions[parent_hash]
                        if parent_pos > i:
                            # Draw line to parent
                            for j in range(i + 1, parent_pos):
                                if line[j] == " ":
                                    line[j] = "|"
                            line[parent_pos] = "\\"
            
            # Convert to string
            graph_str = "".join(line)
            
            # Format commit info
            short_hash = commit_hash[:7]
            message = commit['message'].split('\n')[0]
            branch_info = f" ({current_branch})" if is_head else ""
            
            # Print with graph
            print(f"{graph_str} {short_hash}{branch_info} {message}")
