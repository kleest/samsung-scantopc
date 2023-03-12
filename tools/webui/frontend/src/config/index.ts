import {AxiosRequestConfig} from "axios";

export interface ApiConfiguration extends AxiosRequestConfig {

}
export interface Configuration {
    api : ApiConfiguration,
}

const createConfig = () : Configuration  => {
    return {
        api: {
            baseURL: process.env.REACT_APP_API_BASE_URL
        },
    };
};

export default createConfig;
