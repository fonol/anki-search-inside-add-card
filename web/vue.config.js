module.exports = {
    chainWebpack: config => { config.optimization.delete('splitChunks') },
    filenameHashing: false,
    outputDir: 'dist/vuejs/',
    configureWebpack: {
        optimization: { splitChunks: false },
        resolve: { alias: { 'vue$': 'vue/dist/vue.esm.js' } }
    },
    pages: {
        main: {
            entry: 'src/vue_main.js',
            output: {
                filename: "siac-vue.js",
            },
        },
    }
}   