import requests
import csv

API_KEY = "YOUR_TMDB_API_KEY"
COUNTRY = "US"             
NETFLIX_PROVIDER_ID = 8     

def get_top_netflix(content_type="movie", pages=3):
    results = []

    for page in range(1, pages + 1):
        url = f"https://api.themoviedb.org/3/discover/{content_type}"
        params = {
            "api_key": API_KEY,
            "with_watch_providers": NETFLIX_PROVIDER_ID,
            "watch_region": COUNTRY,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 200,
            "page": page
        }
        r = requests.get(url, params=params)
        data = r.json()

        for item in data.get("results", []):
            results.append({
                "title": item.get("title") or item.get("name"),
                "rating": item.get("vote_average"),
                "votes": item.get("vote_count"),
                "release_date": item.get("release_date") or item.get("first_air_date"),
                "type": content_type.upper(),
            })

    return results


# Fetch data
movies = get_top_netflix("movie", pages=3)
shows  = get_top_netflix("tv", pages=3)

# Merge + sort
all_titles = sorted(movies + shows, key=lambda x: x["rating"], reverse=True)

# Write CSV
csv_filename = "top_netflix_titles.csv"
with open(csv_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["title", "type", "rating", "votes", "release_date"]
    )
    writer.writeheader()
    writer.writerows(all_titles)

print(f"Saved {len(all_titles)} rows → {csv_filename}")
