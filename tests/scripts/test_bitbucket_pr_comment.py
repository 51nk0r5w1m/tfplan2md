import unittest
from module_loader import load_script_module


class BitbucketPrCommentTests(unittest.TestCase):
    def test_large_report_falls_back_to_html_artifact_link(self):
        module = load_script_module("bitbucket_pr_comment", "bitbucket-pr-comment.py")

        comment = module.build_comment_body(
            report="x" * 100,
            title="Terraform plan report",
            marker="<!-- marker -->",
            max_comment_chars=50,
            artifact_url="https://bitbucket.org/example/repo/pipelines/results/123?tab=artifacts&file=report.md",
        )

        self.assertIn(
            '<a href="https://bitbucket.org/example/repo/pipelines/results/123?tab=artifacts&amp;file=report.md">tfplan2md report artifact</a>',
            comment,
        )
        self.assertIn("Artifact URL: https://bitbucket.org/example/repo/pipelines/results/123?tab=artifacts&file=report.md", comment)

    def test_small_report_is_kept_inline(self):
        module = load_script_module("bitbucket_pr_comment", "bitbucket-pr-comment.py")

        comment = module.build_comment_body(
            report="## Summary\n\nNo changes",
            title="Terraform plan report",
            marker="<!-- marker -->",
            max_comment_chars=1000,
            artifact_url=None,
        )

        self.assertIn("## Summary", comment)
        self.assertNotIn("<a href=", comment)

    def test_oidc_token_is_preferred_for_auth_header(self):
        module = load_script_module("bitbucket_pr_comment", "bitbucket-pr-comment.py")

        auth_header = module.get_auth_header("oidc-token", "user", "password", "fallback-token")

        self.assertEqual("Bearer oidc-token", auth_header)


if __name__ == "__main__":
    unittest.main()
