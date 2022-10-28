# tsptw-streamlit
Web app with streamlit to solve the traveling salesman problem with time windows and steps

## Demo
```
streamlit run main.py
```

## Tips
### Streamlit
[Streamlitの使い方の細かいところ](https://zenn.dev/ohtaman/articles/streamlit_tips)

### Firestore
To import/export data from/to Firestore, write the following in ```docker-compose.yml```
```yaml
services:
  export:
    image: "ghcr.io/tk42/firestore-import-export"
    command: ["node", "export.js", "collecton_name"]
    volumes:
      - ./serviceAccountKey.json:/home/serviceAccountKey.json

  import:
    image: "ghcr.io/tk42/firestore-import-export"
    command: ["node", "import.js", "./import-to-firestore.json"]
    volumes:
      - ./serviceAccountKey.json:/home/serviceAccountKey.json
      - ./import-to-firestore.json:/home/import-to-firestore.json
```