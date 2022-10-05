import '../../index.scss'
import React from 'react'
import {createRoot} from "react-dom/client";
import Manage from "./Manage";
import ContainBack from "../../components/ContainBack";

const container = document.getElementById('root')
const root = createRoot(container!)
root.render(<React.StrictMode>
    <ContainBack component={<Manage />} />
</React.StrictMode>)