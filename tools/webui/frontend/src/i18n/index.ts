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
                "buttonDelete": "Delete document",
                "buttonPreview": "Preview",
                "buttonMerge": "Merge documents",
                "table": {
                    "name": "Name",
                    "url": "Link",
                    "preview": "Preview",
                }
            },
            "list": {
                "empty": "Empty list",
            },
            "dialog": {
                "merge": {
                    "title": "Merge Documents",
                    "contentText": "Select documents to merge in a file under the given name. Documents may also be reordered to define order in final" +
                        " document.",
                    "addDocument": "Add document",
                    "mergedName": "Merged document file name"
                },
                "confirmDeletion": {
                    "title": "Delete Document?",
                    "contentText": "Do you really want to delete {{name}}?",
                },
            },
            "action": {
                "ok": "OK",
                "cancel": "Cancel"
            }
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
                "buttonDelete": "Dokument löschen",
                "buttonPreview": "Vorschau",
                "buttonMerge": "Dokumente zusammenführen",
                "table": {
                    "name": "Name",
                    "url": "Link",
                    "preview": "Vorschau",
                }
            },
            "list": {
                "empty": "Leere Liste",
            },
            "dialog": {
                "merge": {
                    "title": "Dokumente zusammenführen",
                    "contentText": "Dokumente zum Zusammenführen im angegebenen Dateinamen auswählen. Die Reihenfolge der Dokumente im erzeugten Dokument" +
                        " kann angepasst werden.",
                    "addDocument": "Dokument hinzufügen",
                    "mergedName": "Dateiname des erzeugten Dokuments"
                },
                "confirmDeletion": {
                    "title": "Dokument löschen?",
                    "contentText": "Dokument {{name}} wirklich löschen?",
                },
            },
            "action": {
                "ok": "OK",
                "cancel": "Abbrechen"
            }
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
