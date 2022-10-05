import '../../index.scss'
import React from 'react'
import {createRoot} from "react-dom/client";
import Email from "./Email";
import ContainBack from "../../components/ContainBack";

const container = document.getElementById('root')
const root = createRoot(container!)
root.render(<React.StrictMode>
    <ContainBack component={<Email />} />
</React.StrictMode>)