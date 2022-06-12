import {BuildConfig as common} from "../common/index.js"

export const BuildConfig = {
    ...common,
    flavor: 'PROD',
    API_BASE_URL: '/api/'
};
