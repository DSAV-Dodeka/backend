import React, {ReactNode} from "react";
import Back from "./Back";

type Props = {
    component: ReactNode;
}

const ContainBack: React.FC<Props> = (props)  => {

    return (
        <div className="container">
            <div className="containerC"><Back/></div>
            <div className="page">{props.component}</div>
            <div className="containerC"></div>
        </div>
)
}

export default ContainBack;




