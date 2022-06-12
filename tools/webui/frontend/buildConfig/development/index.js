import {BuildConfig as common} from "../common/index.js"

export const BuildConfig = {
    ...common,
    flavor: 'DEV',
    API_BASE_URL: '/api/'
};
