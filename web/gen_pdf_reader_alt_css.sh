#!/bin/bash

# lightblue theme
rm -f 'pdf_reader_lightblue.css'
cp 'pdf_reader.css' 'pdf_reader_lightblue.css'
# replace styles
sed -i 's/darkorange/#41b3a3/' 'pdf_reader_lightblue.css' 
sed -i 's/orange/#85cdca/' 'pdf_reader_lightblue.css' 


# khaki theme
rm -f 'pdf_reader_khaki.css'
cp 'pdf_reader.css' 'pdf_reader_khaki.css'
# replace styles
sed -i 's/darkorange/#f6d198/' 'pdf_reader_khaki.css' 
sed -i 's/orange/#f6d198/' 'pdf_reader_khaki.css' 


# tan theme
rm -f 'pdf_reader_tan.css'
cp 'pdf_reader.css' 'pdf_reader_tan.css'
# replace styles
sed -i 's/darkorange/#cfb495/' 'pdf_reader_tan.css' 
sed -i 's/orange/#cfb495/' 'pdf_reader_tan.css' 

# darkseagreen theme
rm -f 'pdf_reader_darkseagreen.css'
cp 'pdf_reader.css' 'pdf_reader_darkseagreen.css'
# replace styles
sed -i 's/darkorange/#9dab86/' 'pdf_reader_darkseagreen.css' 
sed -i 's/orange/#9dab86/' 'pdf_reader_darkseagreen.css' 

# lightgreen theme
rm -f 'pdf_reader_lightgreen.css'
cp 'pdf_reader.css' 'pdf_reader_lightgreen.css'
# replace styles
sed -i 's/darkorange/#9dab86/' 'pdf_reader_lightgreen.css' 
sed -i 's/orange/#9dab86/' 'pdf_reader_lightgreen.css' 

# lightsalmon theme
rm -f 'pdf_reader_lightsalmon.css'
cp 'pdf_reader.css' 'pdf_reader_lightsalmon.css'
# replace styles
sed -i 's/darkorange/#ffb385/' 'pdf_reader_lightsalmon.css' 
sed -i 's/orange/#ffb385/' 'pdf_reader_lightsalmon.css' 

# yellow theme
rm -f 'pdf_reader_yellow.css'
cp 'pdf_reader.css' 'pdf_reader_yellow.css'
# replace styles
sed -i 's/darkorange/#ffd868/' 'pdf_reader_yellow.css' 
sed -i 's/orange/#ffd868/' 'pdf_reader_yellow.css' 

# crimson theme
rm -f 'pdf_reader_crimson.css'
cp 'pdf_reader.css' 'pdf_reader_crimson.css'
# replace styles
sed -i 's/darkorange/#c72c41/' 'pdf_reader_crimson.css' 
sed -i 's/orange/#c72c41/' 'pdf_reader_crimson.css' 

# steelblue theme
rm -f 'pdf_reader_steelblue.css'
cp 'pdf_reader.css' 'pdf_reader_steelblue.css'
# replace styles
sed -i 's/darkorange/#2496dc/' 'pdf_reader_steelblue.css' 
sed -i 's/orange/#2496dc/' 'pdf_reader_steelblue.css' 