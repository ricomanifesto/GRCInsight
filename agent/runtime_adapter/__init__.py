"""Local synthetic MVP: GRC report execution through a leased workflow API.

A narrow Python adapter around the real ``run_grc_analysis_endpoint``: product
admission and cancellation, a Runtime worker with leases and recovery, a durable
product outcome store, and a reader. External feed, model and enrichment
boundaries are synthetic. The Go API, FastAPI routes, Lambda handler, DynamoDB
and publication workflows are not wired to it.
"""
