# Newspaper Comments
This repository contains a collection of scripts to scrape comments from (currently only Zeit-Online) newspapers and subsequently store and visualize them for analysis.

## Project Structure

1. **Scraper.py**: Scrape comments from Zeit-Online. 
2. **Setup_SQL.py**: Setting up the SQL database. 
3. **Ingest_Data.py**: Ingest the scraped data and load it into a PostgreSQL database.

The project is transitioning to Google Cloud Services. Here's the current progress:

- [x] **Google Cloud Storage**: A bucket has been set up to store the comment JSON files.
- [x] **Scraper Adaptation**: The script has been adapted to save scraped data directly to the GCS bucket.
- [x] **Dockerized Scraper Deployment**: A docker image encapsulating the scraper script has been added to the Google Artifact Registry. It is configured to run every 8 hours as a job on Googles Cloud Run to collect new comments and add them to the bucket.
- [ ] Load the JSON comment data from the GCS bucket into Google BigQuery.
- [ ] Implement a data visualization dashboard for insights on top of big query.
- [ ] Possibly introduce orchestration of jobs using Apache Airflow.


