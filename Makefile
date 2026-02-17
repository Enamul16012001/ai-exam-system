docker-up:
	docker compose down && docker compose up --build -d

docker-logs:
	docker compose logs -f

git-push:
	git add . && git commit -m "Modified Backend" && git push -u origin v2