import typer
import logging
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
import os
from dotenv import load_dotenv

from core.fetcher import LeadFetcher
from core.enricher import LeadEnricher
from core.intent import IntentAnalyzer
from core.exporter import CSVExporter

# Load environment variables
load_dotenv()

# Setup rich console and logging
console = Console()
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
logger = logging.getLogger("leadgen")

app = typer.Typer(help="A CLI tool to fetch, enrich, qualify, and export leads.")

@app.command()
def generate(
    keywords: str = typer.Option(..., "--keywords", "-k", help="Keywords to search for (e.g., 'SaaS, AI')"),
    title: str = typer.Option(..., "--title", "-t", help="Target job title (e.g., 'CTO')"),
    source: str = typer.Option("github", "--source", "-s", help="Source platform to search (github, linkedin, twitter)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of leads to fetch"),
    output: str = typer.Option("leads.csv", "--output", "-o", help="Output CSV filename")
):
    """
    Fetches leads, enriches them, confirms buying signals, and exports to CSV.
    """
    console.print(f"[bold green]Starting Lead Generation Pipeline[/bold green]")
    console.print(f"Keywords: [bold blue]{keywords}[/bold blue] | Title: [bold blue]{title}[/bold blue] | Source: [bold blue]{source}[/bold blue] | Limit: [bold blue]{limit}[/bold blue]\n")
    
    # 1. Fetch
    with console.status("[bold cyan]Fetching leads...[/bold cyan]"):
        fetcher_api_key = os.getenv("LEAD_API_KEY")
        fetcher = LeadFetcher(api_key=fetcher_api_key)
        raw_leads = fetcher.fetch_leads(keywords=keywords, title=title, source=source.lower(), limit=limit)
    
    if not raw_leads:
        console.print("[bold red]No leads found.[/bold red]")
        raise typer.Exit()
        
    console.print(f"[green]Found {len(raw_leads)} initial prospects.[/green]")

    # 2. Enrich
    with console.status("[bold cyan]Enriching prospects with additional data...[/bold cyan]"):
        enricher_api_key = os.getenv("ENRICHMENT_API_KEY")
        enricher = LeadEnricher(api_key=enricher_api_key)
        enriched_leads = enricher.enrich(raw_leads)
        
    console.print(f"[green]Enriched data for {len(enriched_leads)} prospects.[/green]")

    # 3. Analyze Intent
    with console.status("[bold cyan]Analyzing intent and buying signals...[/bold cyan]"):
        openai_key = os.getenv("OPENAI_API_KEY")
        analyzer = IntentAnalyzer(openai_api_key=openai_key)
        qualified_leads = analyzer.score_intent(enriched_leads, keywords=keywords)
        
    console.print(f"[green]Found {len(qualified_leads)} qualified leads with strong buying signals.[/green]\n")

    # Display results
    table = Table(title="Qualified Leads")
    table.add_column("Name", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Company", style="green")
    table.add_column("Intent Score", justify="right", style="yellow")
    
    for lead in qualified_leads:
        table.add_row(
            f"{lead['first_name']} {lead['last_name']}",
            lead['title'],
            lead['company'],
            str(lead.get('intent_score', 'N/A'))
        )
        
    console.print(table)
    console.print("\n")

    # 4. Export
    with console.status("[bold cyan]Exporting to CSV...[/bold cyan]"):
        exporter = CSVExporter()
        exporter.export(qualified_leads, output)
        
    console.print(f"[bold green]Pipeline complete! Leads exported to {output}[/bold green]")

if __name__ == "__main__":
    app()
