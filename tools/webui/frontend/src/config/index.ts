// @ts-ignore
import {BuildConfig} from "buildConfig";
import {AxiosRequestConfig} from "axios";

export interface ApiConfiguration extends AxiosRequestConfig {

}
export interface Configuration {
    api : ApiConfiguration,
}

const createConfig = () : Configuration  => {
    return {
        api: {
            baseURL: BuildConfig.API_BASE_URL
        },
    };
};

export default createConfig;
