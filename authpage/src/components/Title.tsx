
import Logo from "../logo.svg?react"

interface TitleProps {
    title: string
}


const Title = (props: TitleProps) => {

    return (
        <div className="titleBar"><div className="logo"><Logo /></div><h1 className="title">{props.title}</h1></div>
    )
}

export default Title;




