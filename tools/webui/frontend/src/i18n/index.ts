import i18n from 'i18next';
import {initReactI18next} from "react-i18next";
import LanguageDetector from 'i18next-browser-languagedetector';

export const resources = {
    en: {
        translations: {
            "appName": "Samsung ScanToPC WebUI",
            "documents": {
                "titleList": "Documents",
                "titleOutList": "Documents in Output Directory",
                "buttonSave": "Save",
                "buttonLoad": "Refresh list",
                "buttonSendToOutDir": "Send to output directory",
                "buttonPreview": "Preview",
                "table": {
                    "name": "Name",
                    "url": "Link",
                    "preview": "Preview",
                }
            },
        }
    },
    de: {
        translations: {
            "documents": {
                "titleList": "Dokumente",
                "titleOutList": "Dokumente im Ausgabeverzeichnis",
                "buttonSave": "Speichern",
                "buttonLoad": "Liste aktualisieren",
                "buttonSendToOutDir": "In Ausgabeverzeichnis verschieben",
            },
        }
    }
};

// https://www.i18next.com/overview/typescript#argument-of-type-defaulttfuncreturn-is-not-assignable-to-parameter-of-type-xyz
declare module 'i18next' {
    interface CustomTypeOptions {
        returnNull: false;
    }
}

i18n
    .use(initReactI18next)
    .use(LanguageDetector)
    .init({
        fallbackLng: 'en',
        debug: true,

        // have a common namespace used around the full app
        ns: ['translations'],
        defaultNS: 'translations',

        interpolation: {
            escapeValue: false, // XSS protection not needed for react
        },

        returnNull: false,

        resources,
    });

export default i18n;
