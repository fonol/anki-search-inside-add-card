## Important notice
> Some of the config values can be changed through the add-ons interface (either through the settings dialog or they just represent some current UI settings).
> That is why only some options that cannot be set through the add-on interface are explained here.

### decks
If you only want to use certain decks for the search index, change this option. It accepts a list of deck names, 
e.g. ["myDeck_1", "myDeck_2"]

### imageMaxHeight 
Maximum height in pixels that images in the displayed results should have.

### numberOfResults
Maximum number of search results. Default: 1000

### pdf.clozegen.notetype
The exact name of the notetype that shall be used for the "Generate Clozes" function.
If this is not set (default), the add-on will search for a notetype named "Cloze"

### pdf.clozegen.field.clozedtext
The exact name of the field where the cloze text should go.
If this is not set (default), the add-on will search for a field named "Text".

### pdf.clozegen.field.page
The exact name of the field where the page on which the cloze has been generated should go.
If this is not set (default), the add-on will not attempt to insert the page in the note.

### pdf.clozegen.field.pdfpath
The exact name of the field where the cloze text should go.
If this is not set (default), the add-on will not attempt to insert the pdf path in the note.

### pdf.clozegen.field.pdftitle
The exact name of the field where the cloze text should go.
If this is not set (default), the add-on will not attempt to insert the pdf title in the note.

### pdf.onOpen.autoFillFieldsWithPDFName
If not empty, when a PDF is opened, and the current note contains one of the given fields, fill this field with the PDF title.

### pdfUrlImportSavePath
If you use the "import PDF from webpage" functionality, this specifies the folder where the generated PDFs will be saved.

### searchUrls
Takes a list of URLs that are used in the pdf reader to do web queries. Not all websites allow to be embedded, e.g. Google does not, but some useful ones like Wikipedia do. To run a query, replace the query part in the URL with "[QUERY]".
Example from the default config:
"https://en.wikipedia.org/w/index.php?search=[QUERY]&title=Special%3ASearch&go=Go&ns0=1"
[QUERY] will be replaced by your search terms.

### pdf.import.folders_to_search
Accepts a list of folder names, that will be scanned for .pdf files if you open the "PDF Import" tab on the sidebar.

### usePorterStemmer
If you set this to true, the search library will use the Porter Stemmer. The stemmer is best suited for english, so for other languages, your mileage may vary, and it might increase indexing time. What it does is to reduce words to some kind of base form, so you can increase your search recall: E.g. "increase" and "increasing" both get reduced to "increas", and so either will find the other term too. The stemmer starts working after you rebuilt your index.

### freezeIndex
If you, for some reason, don't want the index to be rebuilt under any circumstances on startup, set this to true.

### shortcuts.<xyz>
Shortcuts for some different functions. If you change these, maybe check for possible conflicts with existing shortcuts in the editor before.

### pdf.highlights.use_alt_render
For some reason, the highlights are not displaying correctly on some environments (highlights cover up the highlighted text). Until the issue is resolved, you can set this option to true, which will make the PDF reader use an alternative way of displaying the highlights (might not look as good as the default mode though).

### searchbar.default_mode 
Determines what mode (Add-on or Browser) the searchbar at the bottom of the UI will have on Anki startup.

### mix_reviews_and_reading
If true, while in review, the add-on will ask you at regular intervals if you want to open the next item in the queue, that way, you can interleave 
working on your queue and reviewing.

### mix_reviews_and_reading.interrupt_every_nth_card
Determines after how many cards you will be interrupted and asked if you want to open the queue.

### anki.editor.remember_location
If true, the "Edit Note" dialog will remember its last location and size (this does not persist after closing Anki).