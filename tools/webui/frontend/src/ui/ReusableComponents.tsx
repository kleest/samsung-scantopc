import {Stack, StackProps, styled} from "@mui/material";

export const FlexStack = styled(Stack)<StackProps>({display: "flex", "& > *": {flex: "1"}});
export const GrowingSpace = styled("div")({
    flex: "1 1 auto"
});
