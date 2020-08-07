const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const OptimizeCSSAssetsPlugin = require("optimize-css-assets-webpack-plugin");



module.exports = {
    entry: ['./src/entry.js'],
    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: 'siac.min.js',
		libraryTarget: 'window'
    },
    mode: "production",
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: [MiniCssExtractPlugin.loader, 'css-loader'],
              },
           
        ],
    },
    plugins: [
        new MiniCssExtractPlugin({ filename: 'styles.min.css'})
    ],
    optimization: {
        minimizer: [
          
            new OptimizeCSSAssetsPlugin({})
        ]
    },
  
};