IMAGE_NAME = ynab-streamlit
PORT = 8501

.PHONY: build run stop logs

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run --rm -d -p $(PORT):$(PORT) --env-file .env $(IMAGE_NAME)

stop:
	docker stop $$(docker ps -q --filter ancestor=$(IMAGE_NAME))

logs:
	docker logs -f $$(docker ps -q --filter ancestor=$(IMAGE_NAME))
