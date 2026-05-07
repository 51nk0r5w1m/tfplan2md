using AwesomeAssertions;
using Oocx.TfPlan2Md.RenderTargets.Bitbucket;
using TUnit.Core;

namespace Oocx.TfPlan2Md.Tests.RenderTargets;

/// <summary>
/// Tests for <see cref="BitbucketMarkdownPostProcessor"/> to ensure Bitbucket-safe markdown rewrites preserve content.
/// </summary>
public class BitbucketMarkdownPostProcessorTests
{
    /// <summary>
    /// Verifies HTML details and summary wrappers are flattened to plain markdown headings.
    /// </summary>
    [Test]
    public async Task Process_WithDetailsBlock_FlattensSummaryAndRemovesHtmlContainer()
    {
        var markdown = "<details open><summary>### Resource Summary</summary><br>content</details>";

        var result = BitbucketMarkdownPostProcessor.Process(markdown);

        result.Should().Be("\n\n### Resource Summary\n\ncontent");

        await Task.CompletedTask;
    }

    /// <summary>
    /// Verifies inline code preserves decoded characters that markdown code spans render literally.
    /// </summary>
    [Test]
    public async Task Process_WithInlineCodeContainingAmpersandAndPipe_PreservesLiteralCharacters()
    {
        var markdown = "Value: <code>a&amp;b|c</code>";

        var result = BitbucketMarkdownPostProcessor.Process(markdown);

        result.Should().Be("Value: `a&b|c`");

        await Task.CompletedTask;
    }

    /// <summary>
    /// Verifies inline code chooses a long-enough fence when the content contains backticks.
    /// </summary>
    [Test]
    public async Task Process_WithInlineCodeContainingBackticks_UsesLongerFenceWithoutEscapingContent()
    {
        var markdown = "Value: <code>prefix `quoted` suffix</code>";

        var result = BitbucketMarkdownPostProcessor.Process(markdown);

        result.Should().Be("Value: ``prefix `quoted` suffix``");

        await Task.CompletedTask;
    }

    /// <summary>
    /// Verifies block code is converted to fenced markdown while preserving decoded newlines.
    /// </summary>
    [Test]
    public async Task Process_WithPreCodeBlock_ConvertsToMarkdownFence()
    {
        var markdown = "<pre><code>line 1&lt;br/&gt;line 2\nline 3</code></pre>";

        var result = BitbucketMarkdownPostProcessor.Process(markdown);

        result.Should().Be("```\nline 1\nline 2\nline 3\n```");

        await Task.CompletedTask;
    }

    /// <summary>
    /// Verifies unsupported inline HTML is rewritten to markdown-only equivalents.
    /// </summary>
    [Test]
    public async Task Process_WithBoldSpanAndBreak_RewritesMarkupToPlainMarkdown()
    {
        var markdown = "<span>Start</span> <b>bold</b><br/>next";

        var result = BitbucketMarkdownPostProcessor.Process(markdown);

        result.Should().Be("Start **bold** / next");

        await Task.CompletedTask;
    }

    /// <summary>
    /// Verifies a realistic report fragment keeps tables, code fences, findings, and debug content while removing unsupported HTML.
    /// </summary>
    [Test]
    public async Task Process_WithRealisticReportFragment_PreservesMarkdownAndRemovesUnsupportedHtml()
    {
        var markdown = """
            # Terraform Plan Report

            | Action | Count |
            | ------ | ----- |
            | ➕ Add | 1 |

            <details><summary>### azurerm_storage_account.example</summary><br>

            | Attribute | Before | After |
            | --------- | ------ | ----- |
            | `name` | <code>old</code> | <code>new</code> |

            <pre><code>- allow_http = true&lt;br/&gt;+ allow_https = true</code></pre>

            <b>Checkov CKV_AZURE_1</b><br/>Storage account should use secure transfer.
            </details>

            <details><summary>🐛 Debug Information</summary><br>
            Renderer: <code>DefaultResourceRenderer</code>
            </details>
            """;

        var result = BitbucketMarkdownPostProcessor.Process(markdown);

        result.Should().Contain("| Action | Count |");
        result.Should().Contain("### azurerm_storage_account.example");
        result.Should().Contain("`name`");
        result.Should().Contain("`old`");
        result.Should().Contain("```\n- allow_http = true\n+ allow_https = true\n```");
        result.Should().Contain("**Checkov CKV_AZURE_1** / Storage account should use secure transfer.");
        result.Should().Contain("🐛 Debug Information");
        result.Should().Contain("`DefaultResourceRenderer`");
        result.Should().NotContain("<details");
        result.Should().NotContain("<summary>");
        result.Should().NotContain("<code");
        result.Should().NotContain("<pre");
        result.Should().NotContain("<b>");

        await Task.CompletedTask;
    }
}
