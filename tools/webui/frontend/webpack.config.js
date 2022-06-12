const webpack = require('webpack');
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');

const nodeEnv = process.env.NODE_ENV || "development";
const isDevelopment = nodeEnv !== 'production';

const config = {
    mode: isDevelopment ? 'development' : 'production',
    entry: [
        './src/index.tsx'
    ],
    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: '[name].[contenthash].js'
    },
    module: {
        rules: [
            {
                test: /\.(ts|js)x?$/,
                use: [
                    {
                        loader: require.resolve('babel-loader'),
                        options: {
                            presets: [
                                ["@babel/preset-env", {
                                    "modules": false
                                }],
                                "@babel/preset-typescript",
                                "@babel/preset-react"
                            ],
                            plugins: [
                                isDevelopment && require.resolve('react-refresh/babel'),
                                "@babel/plugin-proposal-class-properties",
                                ["@babel/plugin-transform-runtime", {
                                    "regenerator": true
                                }]
                            ].filter(Boolean),
                            assumptions: {setPublicClassFields: false}
                        },
                    },
                ],
                exclude: /node_modules/
            },
            {
                test: /\.scss$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    'css-loader',
                    'sass-loader'
                ]
            },
            {
                test: /\.css$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    'css-loader'
                ]
            },
            {
                test: /\.png$/,
                use: [
                    {
                        loader: 'url-loader',
                        options: {
                            mimetype: 'image/png'
                        }
                    }
                ]
            },
            {
                test: /\.svg$/,
                use: 'file-loader'
            },
            {
                test: /\.json$/,
                type: 'json'
            }
        ]
    },
    devServer: {
        'static': {
            directory: './dist'
        },
        hot: true,
        proxy: {
            '/api': {
                target: 'http://localhost:3000',
            },
        }
    },
    resolve: {
        extensions: [
            '.tsx',
            '.ts',
            '.jsx',
            '.js'
        ],
        modules: [
            path.resolve(__dirname, 'src/'), 'node_modules'
        ],
        alias: {
            // use config module dependent in NODE_ENV
            buildConfig: path.join(__dirname, 'buildConfig', nodeEnv)
        }
    },
    plugins: [
        new HtmlWebpackPlugin({
            template: __dirname + '/index.html',
        }),
        new MiniCssExtractPlugin(),
        new CleanWebpackPlugin(),
        isDevelopment && new ReactRefreshWebpackPlugin()
    ].filter(Boolean),
    optimization: {
        runtimeChunk: 'single',
        splitChunks: {
            cacheGroups: {
                vendor: {
                    test: /[\\/]node_modules[\\/]/,
                    name: 'vendors',
                    chunks: 'all'
                }
            }
        }
    }
};

module.exports = (env, argv) => {
    if (argv.hot) {
        // Cannot use 'contenthash' when hot reloading is enabled.
        config.output.filename = '[name].[fullhash].js';
    }

    return config;
};
