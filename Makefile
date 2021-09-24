run:
	python app.py

clean:
	rm -f *.html *.txt

reset: clean
	rm -f *.pickle

logout: reset
	rm -f token.json
